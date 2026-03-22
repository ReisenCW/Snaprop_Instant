"""
批量生成反思数据，丰富向量数据库
选取上海6个代表性区域进行预测
"""
import asyncio
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_prediction.api import predict_region

# 选取的6个代表性区域
REGIONS = [
    "2025年上半年上海陆家嘴房价走势如何",
    "2025年上半年上海张江高科技园区房价走势如何", 
    "2025年上半年上海临港新城房价走势如何",
    "2025年上半年上海嘉定新城房价走势如何",
    "2025年上半年上海虹口北外滩房价走势如何",
    "2025年上半年上海徐家汇房价走势如何",
]

def run_batch_prediction():
    """批量执行预测"""
    print("=" * 60)
    print("批量生成反思数据 - 丰富向量数据库")
    print("=" * 60)
    
    for i, query in enumerate(REGIONS, 1):
        print(f"\n[{i}/{len(REGIONS)}] 正在预测: {query}")
        print("-" * 40)
        
        try:
            # 使用进化模式（enable_evolution=True）来生成反思
            result = predict_region(query, enable_evolution=True, debug=True)
            print(f"预测结果: {result[:100]}..." if len(result) > 100 else f"预测结果: {result}")
            print(f"✓ {query} 预测完成")
        except Exception as e:
            print(f"✗ {query} 预测失败: {e}")
        
        # 避免 API 调用过快
        if i < len(REGIONS):
            print("等待 2 秒...")
            import time
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("批量预测完成！")
    print("=" * 60)


if __name__ == "__main__":
    run_batch_prediction()
