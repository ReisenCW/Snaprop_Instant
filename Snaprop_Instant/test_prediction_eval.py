"""
LLM 房价趋势预测评估脚本
评估 llm_prediction 模块的预测准确性

运行方式:
    cd Snaprop_Instant
    python test_prediction_eval.py
"""
import asyncio
import json
import re
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_prediction.api import predict_region_async
from llm_prediction.agents.search_agent import SearchAgent
from llm_prediction.config import Config


REGIONS = [
    "上海市杨浦区五角场",
    "上海市浦东新区陆家嘴",
    "上海市徐汇区徐家汇",
    "上海市静安区南京西路",
    "上海市黄浦区外滩",
    "上海市长宁区虹桥",
    "上海市普陀区长征",
    "上海市虹口区四川北路",
    "上海市闵行区莘庄",
    "上海市宝山区大场",
]

TIME_PERIODS = ["2025年1月-6月", "2025年7月-12月"]


def _parse_single_phase(text: str):
    """
    解析单个阶段的幅度值（返回小数，如 0.025 表示 +2.5%）
    返回 None 如果无法解析
    """
    # 匹配范围 "1%~3%" 或 "1%-3%"
    range_m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*[-~至]\s*(\d+(?:\.\d+)?)\s*%', text)
    if range_m:
        val = (float(range_m.group(1)) + float(range_m.group(2))) / 2.0 / 100.0
        return val

    # 匹配单个值 "约X%"、"X%左右"
    single_m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*左右?', text)
    if single_m:
        return float(single_m.group(1)) / 100.0

    # 匹配 "涨幅X%"、"跌幅X%"
    magnitude_m = re.search(r'[涨跌]幅?\s*(\d+(?:\.\d+)?)\s*%', text)
    if magnitude_m:
        return float(magnitude_m.group(1)) / 100.0

    return None


def parse_trend(text: str):
    """
    从趋势文本提取幅度值（返回小数，如 0.025 表示 +2.5%）
    对于"先涨X%再跌Y%"这类分段预测，返回净幅度（如先涨2%再跌1% -> 涨1%）
    返回 None 如果无法解析
    """
    if not text:
        return None

    # 去除换行，统一空白
    text = text.strip().replace('\n', ' ')

    # 匹配 "基本持平" 类 → 返回 0
    if '基本持平' in text:
        # 尝试提取 "X%以内"
        m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*以内', text)
        if m:
            val = float(m.group(1)) / 100.0
            return val
        return 0.0

    # 检测"先...后..."分段格式
    multi_phase_m = re.search(r'先(.+?)后(.+)', text)
    if multi_phase_m:
        phase1_text = multi_phase_m.group(1)
        phase2_text = multi_phase_m.group(2)

        # 解析第一阶段方向和幅度
        p1_rise = bool(re.search(r'上升|上涨|增长', phase1_text))
        p1_fall = bool(re.search(r'下降|下跌|减少', phase1_text))
        p1_dir = 1 if p1_rise else (-1 if p1_fall else 0)
        p1_mag = _parse_single_phase(phase1_text)

        # 解析第二阶段方向和幅度
        p2_rise = bool(re.search(r'上升|上涨|增长', phase2_text))
        p2_fall = bool(re.search(r'下降|下跌|减少', phase2_text))
        p2_dir = 1 if p2_rise else (-1 if p2_fall else 0)
        p2_mag = _parse_single_phase(phase2_text)

        # 净幅度 = 各阶段幅度之和（方向已在dir中）
        net = 0.0
        if p1_dir != 0 and p1_mag is not None:
            net += p1_dir * p1_mag
        if p2_dir != 0 and p2_mag is not None:
            net += p2_dir * p2_mag

        # 如果解析失败，尝试降级为整体解析
        if net == 0.0 and (p1_mag is None and p2_mag is None):
            return _parse_trend_single_phase(text)

        return net

    return _parse_trend_single_phase(text)


def _parse_trend_single_phase(text: str):
    """解析单阶段趋势文本的幅度值"""
    # 确定方向：上升/上涨/增长 vs 下降/下跌/减少
    is_rise = bool(re.search(r'上升|上涨|增长', text))
    is_fall = bool(re.search(r'下降|下跌|减少', text))

    if not is_rise and not is_fall:
        return None

    direction = 1 if is_rise else -1

    mag = _parse_single_phase(text)
    if mag is not None:
        return direction * mag

    return None


def classify_trend(text: str):
    """
    将趋势文本分类为: 'rise'(涨), 'fall'(跌), 'stable'(持平)
    对于分段预测（如"先涨后跌"），根据净幅度判断方向
    """
    if not text:
        return 'unknown'
    text = text.strip()
    if '持平' in text:
        return 'stable'

    # 检测"先...后..."分段格式，根据净幅度判断
    multi_phase_m = re.search(r'先(.+?)后(.+)', text)
    if multi_phase_m:
        phase1_text = multi_phase_m.group(1)
        phase2_text = multi_phase_m.group(2)

        p1_rise = bool(re.search(r'上升|上涨|增长', phase1_text))
        p1_fall = bool(re.search(r'下降|下跌|减少', phase1_text))
        p1_dir = 1 if p1_rise else (-1 if p1_fall else 0)
        p1_mag = _parse_single_phase(phase1_text)

        p2_rise = bool(re.search(r'上升|上涨|增长', phase2_text))
        p2_fall = bool(re.search(r'下降|下跌|减少', phase2_text))
        p2_dir = 1 if p2_rise else (-1 if p2_fall else 0)
        p2_mag = _parse_single_phase(phase2_text)

        net = 0.0
        if p1_dir != 0 and p1_mag is not None:
            net += p1_dir * p1_mag
        if p2_dir != 0 and p2_mag is not None:
            net += p2_dir * p2_mag

        if abs(net) < 0.0005:  # 净幅度 < 0.05% 视为持平
            return 'stable'
        return 'rise' if net > 0 else 'fall'

    # 单阶段判断
    if bool(re.search(r'上升|上涨|增长', text)):
        return 'rise'
    if bool(re.search(r'下降|下跌|减少', text)):
        return 'fall'
    return 'unknown'


def trend_accuracy(pred_text: str, actual_text: str):
    """
    计算趋势准确率
    完全一致 → 1.0
    一个涨跌、一个持平 → 0.5
    方向相反（涨 vs 跌）→ 0.0
    """
    pred_cat = classify_trend(pred_text)
    actual_cat = classify_trend(actual_text)

    if pred_cat == 'unknown' or actual_cat == 'unknown':
        return 0.0

    if pred_cat == actual_cat:
        return 1.0

    # 一个涨跌、一个持平
    cats = {pred_cat, actual_cat}
    if cats == {'rise', 'stable'} or cats == {'fall', 'stable'}:
        return 0.5

    # 方向相反
    return 0.0


async def get_actual_trend(region: str, time_range: str) -> str:
    """获取真实趋势（联网搜索）"""
    agent = SearchAgent(Config())
    return await agent.get_actual(region, time_range)


async def run_evaluation():
    """主评估流程"""
    all_results = []
    total = len(REGIONS) * len(TIME_PERIODS)
    count = 0

    print(f"开始评估: {total} 次预测（{len(REGIONS)} 地区 × {len(TIME_PERIODS)} 时间段）")
    print("=" * 60)

    for region in REGIONS:
        for period in TIME_PERIODS:
            count += 1
            print(f"[{count}/{total}] {region} - {period}")

            query = f"{period} {region}房价走势如何"

            # 1. 预测
            try:
                pred_text = await predict_region_async(query, enable_evolution=False, debug=False)
            except Exception as e:
                print(f"  预测失败: {e}")
                pred_text = ""

            # 2. 获取真实趋势
            try:
                actual_text = await get_actual_trend(region, period)
            except Exception as e:
                print(f"  获取真实数据失败: {e}")
                actual_text = ""

            pred_val = parse_trend(pred_text)
            actual_val = parse_trend(actual_text)
            acc = trend_accuracy(pred_text, actual_text)

            print(f"  预测值: {pred_val} | 实际值: {actual_val} | 准确率: {acc}")
            print(f"  预测文本: {pred_text[:80] if pred_text else 'N/A'}...")
            print(f"  实际文本: {actual_text[:80] if actual_text else 'N/A'}...")

            all_results.append({
                "region": region,
                "period": period,
                "pred_text": pred_text,
                "actual_text": actual_text,
                "pred_val": pred_val,
                "actual_val": actual_val,
                "accuracy": acc
            })
            print()

    return all_results


def compute_metrics(results):
    """计算评估指标"""
    # 过滤掉无法解析的条目
    valid = [r for r in results if r["pred_val"] is not None and r["actual_val"] is not None]

    if not valid:
        return {"MAE": None, "RMSE": None, "trend_accuracy": None, "valid_count": 0}

    pred_vals = np.array([r["pred_val"] for r in valid])
    actual_vals = np.array([r["actual_val"] for r in valid])

    mae = float(np.mean(np.abs(pred_vals - actual_vals)))
    rmse = float(np.sqrt(np.mean((pred_vals - actual_vals) ** 2)))
    trend_acc = float(np.mean([r["accuracy"] for r in results]))

    return {
        "MAE": round(mae * 100, 2),      # 转为百分比
        "RMSE": round(rmse * 100, 2),    # 转为百分比
        "trend_accuracy": round(trend_acc, 3),
        "valid_count": len(valid),
        "total_count": len(results)
    }


def main():
    results = asyncio.run(run_evaluation())

    metrics = compute_metrics(results)

    output = {
        "summary": metrics,
        "details": results
    }

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("评估完成!")
    print(f"MAE: {metrics['MAE']}% (百分点)" if metrics['MAE'] else "MAE: N/A")
    print(f"RMSE: {metrics['RMSE']}% (百分点)" if metrics['RMSE'] else "RMSE: N/A")
    print(f"趋势准确率: {metrics['trend_accuracy']}" if metrics['trend_accuracy'] else "趋势准确率: N/A")
    print(f"有效解析: {metrics['valid_count']}/{metrics['total_count']}")
    print(f"报告已写入: {output_path}")


if __name__ == "__main__":
    main()
