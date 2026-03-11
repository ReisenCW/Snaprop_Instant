"""
本模块包含智能化市场比较法（IMCA）实现，用于房产估值
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
import os
import sys

# 添加项目根目录到路径，以便导入其他模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rules.differentiable_rule import DifferentiableRuleLearningFramework
except ImportError:
    # 如果规则模块不存在，使用空的框架
    DifferentiableRuleLearningFramework = None

class IMCA:
    """
    智能化市场比较法（Intelligent Market Comparison Approach）
    """
    
    # Feature name mapping for interoperability
    KEY_MAP = {
        'area': ['size', 'house_area', 'area'],
        'floor': ['floor', 'house_floor'],
        'decoration': ['fitment', 'house_decoration', 'decoration'],
        'year': ['built_year', 'built_time', 'house_year', 'year'],
        'location': ['address', 'house_loc', 'location'],
        'time': ['transaction_time', 'time'],
        'type': ['transaction_type', 'type'],
        'green': ['green_rate', 'green']
    }

    # Standardized Mappings
    FLOOR_VALS = {"低": 1, "中": 2, "高": 3}
    DECO_VALS = {"毛坯": 0, "简装": 1, "精装": 2}

    def __init__(self, rule_framework=None):
        """
        初始化IMCA
        
        Args:
            rule_framework: 可微分规则学习框架
        """
        self.rule_framework = rule_framework
        
        # 默认特征权重
        self.default_weights = {
            'location': 0.25,
            'time': 0.15,
            'physical': 0.20,
            'legal': 0.10,
            'environment': 0.15,
            'transaction': 0.15
        }
        
        # 默认特征相似度计算参数
        self.similarity_params = {
            'time_decay_rate': 0.1,
            'distance_decay_rate': 0.2,
            'area_tolerance': 10,
            'floor_importance': 0.5,
            'decoration_importance': 0.7,
            'structure_importance': 0.6,
            'age_importance': 0.6
        }

        # 默认修正系数参数
        self.adjustment_params = {
            'time_factor': 0.08,
            'area_factor': 0.02,
            'floor_factor': 0.02,
            'decoration_factor': 0.1,
            'age_factor': 0.01,
            'green_rate_factor': 0.4,
            'transaction_type_factor': 0.7
        }

    def _get_mapped_val(self, data: Dict[str, Any], key_type: str, default=None) -> Any:
        """Helper to retrieve value using multiple possible keys."""
        for key in self.KEY_MAP.get(key_type, []):
            if key in data and data[key] not in [None, '暂无数据', '未知']:
                return data[key]
        return default

    def _get_numeric_floor(self, floor_val: Any) -> int:
        if isinstance(floor_val, (int, float)): return int(floor_val)
        for k, v in self.FLOOR_VALS.items():
            if k in str(floor_val): return v
        return 2 # Default to Middle

    def _get_numeric_deco(self, deco_val: Any) -> int:
        if isinstance(deco_val, (int, float)): return int(deco_val)
        return self.DECO_VALS.get(str(deco_val), 1) # Default to Simple

    def preprocess_data(self, target_property, comparable_cases):
        """Vectorized preprocessing for efficiency."""
        target = target_property.copy()
        df = pd.DataFrame(comparable_cases)
        
        current_year = datetime.now().year
        
        # Process Target
        built_year = self._get_mapped_val(target, 'year')
        try:
            target['age'] = current_year - int(str(built_year).split('-')[0])
        except (ValueError, TypeError, AttributeError):
            target['age'] = 15 # Default age
        
        # Process Cases
        if not df.empty:
            # Handle Built Year / Age
            def parse_year(v):
                try: return int(str(v).split('-')[0])
                except: return current_year - 15
            
            # Try to find the year column in df
            year_col = next((c for c in df.columns if c in self.KEY_MAP['year']), None)
            if year_col:
                df['age'] = current_year - df[year_col].apply(parse_year)
            else:
                df['age'] = 15

            # Handle Transaction Time
            time_col = next((c for c in df.columns if c in self.KEY_MAP['time']), None)
            if time_col:
                df['transaction_time'] = pd.to_datetime(df[time_col], errors='coerce').fillna(datetime.now())
                df['time_diff'] = (datetime.now() - df['transaction_time']).dt.days / 365.0
            else:
                df['time_diff'] = 0

        return target, df
    
    def calculate_similarity(self, target, case):
        """Calculates similarity between target and a single case with improved consistency."""
        sims = {}
        target_size = self._get_mapped_val(target, 'area')
        case_size = self._get_mapped_val(case, 'area')
        
        # 1. Time Similarity
        time_diff = case.get('time_diff', 0.5)
        sims['time'] = np.exp(-self.similarity_params['time_decay_rate'] * time_diff)
        
        # 2. Location Similarity
        loc_sim = 0.6
        t_loc = str(self._get_mapped_val(target, 'location', '')).lower()
        c_loc = str(self._get_mapped_val(case, 'location', '')).lower()
        
        if t_loc and c_loc:
            if t_loc == c_loc: loc_sim = 1.0
            elif t_loc in c_loc or c_loc in t_loc: loc_sim = 0.9
        
        if 'distance' in case and pd.notnull(case['distance']):
            dist_sim = np.exp(-self.similarity_params['distance_decay_rate'] * float(case['distance']))
            loc_sim = max(loc_sim, dist_sim)
        sims['location'] = loc_sim
        
        # 3. Physical Attributes
        # 3.1 Size
        s_area = 1.0
        if target_size and case_size:
            s_area = np.exp(-abs(float(target_size) - float(case_size)) / self.similarity_params['area_tolerance'])
        
        # 3.2 Floor & Decoration
        t_floor = self._get_numeric_floor(self._get_mapped_val(target, 'floor'))
        c_floor = self._get_numeric_floor(self._get_mapped_val(case, 'floor'))
        s_floor = max(0.3, 1.0 - abs(t_floor - c_floor) * 0.3)
        
        t_deco = self._get_numeric_deco(self._get_mapped_val(target, 'decoration'))
        c_deco = self._get_numeric_deco(self._get_mapped_val(case, 'decoration'))
        s_deco = max(0.3, 1.0 - abs(t_deco - c_deco) * 0.3)
        
        # 3.3 Age
        s_age = 1.0
        t_age = target.get('age')
        c_age = case.get('age')
        if t_age is not None and c_age is not None:
            s_age = np.exp(-abs(t_age - c_age) / 10.0)
            
        # Combine Physical
        p_weight_sum = (1 + self.similarity_params['floor_importance'] + 
                        self.similarity_params['decoration_importance'] + 
                        self.similarity_params['age_importance'])
        sims['physical'] = (s_area + 
                           self.similarity_params['floor_importance'] * s_floor + 
                           self.similarity_params['decoration_importance'] * s_deco + 
                           self.similarity_params['age_importance'] * s_age) / p_weight_sum
        
        # 4. Environment (Green Rate)
        s_env = 1.0
        t_green = self._get_mapped_val(target, 'green')
        c_green = self._get_mapped_val(case, 'green')
        if t_green is not None and c_green is not None:
            try:
                # Handle potential string like "35%"
                tg = float(str(t_green).strip('%')) / 100 if '%' in str(t_green) else float(t_green)
                cg = float(str(c_green).strip('%')) / 100 if '%' in str(c_green) else float(c_green)
                s_env = np.exp(-abs(tg - cg) / 0.1)
            except: pass
        sims['environment'] = s_env
        
        sims['legal'] = 1.0
        
        # 5. Transaction Type
        s_trans = 1.0
        t_type = self._get_mapped_val(target, 'type')
        c_type = self._get_mapped_val(case, 'type')
        if t_type and c_type and t_type != c_type:
            s_trans = 0.7
        sims['transaction'] = s_trans
        
        # Total Weighted Similarity
        total_sim = sum(self.default_weights.get(k, 0) * v for k, v in sims.items())
        return {'similarities': sims, 'total_similarity': total_sim}

    def calculate_adjustment_factors(self, target, case):
        """Calculates adjustment factors with unified mapping logic."""
        adjustments = {}
        
        if self.rule_framework:
            # Rule framework logic (simplified for integration)
            target_results = self.rule_framework.apply_rule_sets(target)
            case_results = self.rule_framework.apply_rule_sets(case)
            
            t_score = next((v["weighted_average"] for v in target_results.values()), 1.0)
            c_score = next((v["weighted_average"] for v in case_results.values()), 1.0)
            
            total_adj = np.clip((t_score + 1e-6) / (c_score + 1e-6), 0.5, 1.5)
            adjustments['total'] = float(total_adj)
            return adjustments

        # Manual Adjustment Logic
        # 1. Time
        time_diff = case.get('time_diff', 0)
        adjustments['time'] = 1.0 + self.adjustment_params['time_factor'] * time_diff
        
        # 2. Area
        t_size = self._get_mapped_val(target, 'area')
        c_size = self._get_mapped_val(case, 'area')
        adjustments['area'] = 1.0
        if t_size and c_size:
            diff = float(t_size) - float(c_size)
            adjustments['area'] = 1.0 - self.adjustment_params['area_factor'] * (diff / 10.0)
            
        # 3. Floor
        t_floor = self._get_numeric_floor(self._get_mapped_val(target, 'floor'))
        c_floor = self._get_numeric_floor(self._get_mapped_val(case, 'floor'))
        adjustments['floor'] = 1.0 + self.adjustment_params['floor_factor'] * (t_floor - c_floor)
        
        # 4. Decoration
        t_deco = self._get_numeric_deco(self._get_mapped_val(target, 'decoration'))
        c_deco = self._get_numeric_deco(self._get_mapped_val(case, 'decoration'))
        adjustments['decoration'] = 1.0 + self.adjustment_params['decoration_factor'] * (t_deco - c_deco)
        
        # 5. Age
        t_age = target.get('age')
        c_age = case.get('age')
        adjustments['age'] = 1.0
        if t_age is not None and c_age is not None:
             adjustments['age'] = 1.0 - self.adjustment_params['age_factor'] * (t_age - c_age)

        # 6. Transaction Type
        t_type = self._get_mapped_val(target, 'type')
        c_type = self._get_mapped_val(case, 'type')
        adjustments['transaction'] = 1.0
        if t_type and c_type and t_type != c_type:
            adjustments['transaction'] = self.adjustment_params['transaction_type_factor']
            
        adjustments['total'] = float(np.prod(list(adjustments.values())))
        return adjustments
        
        adjustments['total'] = total_adjustment
        
        return adjustments
    
    def calculate_weights(self, total_similarities):
        """Calculates case weights using softmax with stability."""
        if not total_similarities: return []
        scores = np.array(total_similarities)
        exp_scores = np.exp(scores - np.max(scores))
        return (exp_scores / np.sum(exp_scores)).tolist()

    def estimate(self, target_property, comparable_cases, pro_adjustments=None):
        """Estimate property value with non-persistent parameter overrides."""
        sim_params = self.similarity_params.copy()
        adj_params = self.adjustment_params.copy()

        if pro_adjustments:
            if 'floor' in pro_adjustments:
                f = pro_adjustments['floor']
                sim_params['floor_importance'] = 0.5 * (f / 0.02)
                adj_params['floor_factor'] = f
            if 'area' in pro_adjustments:
                f = pro_adjustments['area']
                sim_params['area_tolerance'] = 10 * (0.02 / (f if f > 0 else 0.02))
                adj_params['area_factor'] = f
            if 'decoration' in pro_adjustments:
                f = pro_adjustments['decoration']
                sim_params['decoration_importance'] = 0.7 * (f / 0.1)
                adj_params['decoration_factor'] = f
            if 'built_year' in pro_adjustments:
                f = pro_adjustments['built_year']
                sim_params['age_importance'] = 0.6 * (f / 0.01)
                adj_params['age_factor'] = f
            if 'trans_time' in pro_adjustments:
                f = pro_adjustments['trans_time']
                sim_params['time_decay_rate'] = 0.1 * (f / 0.08)
                adj_params['time_factor'] = f
            if 'trans_type' in pro_adjustments:
                adj_params['transaction_type_factor'] = 1.0 - pro_adjustments['trans_type']

        target, df_cases = self.preprocess_data(target_property, comparable_cases)
        if df_cases.empty: return {'estimated_price': None, 'confidence': 0}

        orig_sim, orig_adj = self.similarity_params, self.adjustment_params
        self.similarity_params, self.adjustment_params = sim_params, adj_params

        try:
            results = []
            for _, row in df_cases.iterrows():
                price = row.get('price') or row.get('unit_price')
                sim_data = self.calculate_similarity(target, row)
                adj_data = self.calculate_adjustment_factors(target, row)
                results.append({
                    'similarity': sim_data['total_similarity'],
                    'adjustment': adj_data['total'],
                    'price': price
                })

            weights = self.calculate_weights([r['similarity'] for r in results])
            valid_prices = [r['price'] * r['adjustment'] for i, r in enumerate(results) if r['price']]
            valid_weights = [weights[i] for i, r in enumerate(results) if r['price']]
            
            if not valid_prices: return {'estimated_price': None, 'confidence': 0}
            
            valid_weights = np.array(valid_weights) / np.sum(valid_weights)
            est_price = np.sum(np.array(valid_prices) * valid_weights)
            confidence = np.mean([r['similarity'] for r in results])

            return {
                'estimated_price': float(est_price),
                'confidence': float(confidence),
                'details': {'results': results, 'weights': valid_weights.tolist()}
            }
        finally:
            self.similarity_params, self.adjustment_params = orig_sim, orig_adj
    
    def generate_explanation(self, estimation_result, target_property, comparable_cases):
        """Generates a professional markdown-formatted explanation of the valuation result."""
        if not estimation_result.get('estimated_price'):
            return "无法生成有效估值：未找到足够的可比案例或关键属性缺失。"

        p = estimation_result['estimated_price']
        conf = estimation_result['confidence']
        results = estimation_result['details'].get('results', [])
        weights = estimation_result['details'].get('weights', [])
        
        # Sort results by similarity descending
        # Zip all lists together to sort based on similarity
        if results and weights and len(comparable_cases) == len(results):
            combined = list(zip(results, weights, comparable_cases))
            combined.sort(key=lambda x: x[0].get('similarity', 0), reverse=True)
            results, weights, comparable_cases = zip(*combined)
            # Update the estimation result with sorted details
            estimation_result['details']['results'] = list(results)
            estimation_result['details']['weights'] = list(weights)

        explanation = f"### 智能化市场比较法 (IMCA) 估值深度分析\n\n"
        explanation += f"本次评估采用 **IMCA 算法**，通过多维度非线性修正得出目标房产的参考单价。\n\n"
        explanation += f"**[核心结论]**:\n- **预估单价**: `{p:,.2f}` 元/㎡\n"
        explanation += f"- **综合置信度**: `{conf:.2%}` ({'可靠性高' if conf > 0.8 else ('可靠性中等' if conf > 0.5 else '仅供参考建议')})\n\n"
        
        explanation += "#### 1. 可比案例筛选分析\n"
        explanation += "| 案例 | 位置 | 面积 | 户型 | 楼层 | 装修 | 年份 | 结构 | 绿化 | 原始单价 | 相似度 | 权重 |\n"
        explanation += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        
        weights = estimation_result['details'].get('weights', [])
        for i, res in enumerate(results):
            case = comparable_cases[i]
            addr = str(self._get_mapped_val(case, 'location', '未知地址'))
            size = self._get_mapped_val(case, 'area', '-')
            floor = self._get_mapped_val(case, 'floor', '-')
            deco = self._get_mapped_val(case, 'decoration', '-')
            year = self._get_mapped_val(case, 'year', '-')
            struct = case.get('structure', '-')
            green = case.get('green_rate', '-')
            h_type = self._get_mapped_val(case, 'type', '-') 
            if h_type == '-' or not isinstance(h_type, str):
                h_type = case.get('house_type', '-')
            
            # Format numeric values
            size_str = f"{float(size):.2f}" if size != '-' else '-'
            green_str = f"{float(green):.1%}" if green != '-' and isinstance(green, (int, float)) else str(green)
            price = res.get('price') or 0
            w_val = f"{weights[i]:.1%}" if i < len(weights) else "N/A"
            
            explanation += f"| {i+1} | {addr} | {size_str} | {h_type} | {floor} | {deco} | {year} | {struct} | {green_str} | {price:,.0f} | {res['similarity']:.1%} | {w_val} |\n"
        
        explanation += "\n#### 2. 目标房产特征评估\n"
        
        # Size
        t_size = self._get_mapped_val(target_property, 'area')
        if t_size:
            desc = "稀缺大户型" if float(t_size) > 130 else ("经济小户型" if float(t_size) < 60 else "主流中等户型")
            explanation += f"- **面积区间**: {float(t_size):.2f}㎡，属于{desc}。\n"
            
        # Floor
        t_floor = self._get_mapped_val(target_property, 'floor')
        if t_floor:
            explanation += f"- **楼层分析**: 目标房产位于{t_floor}，"
            explanation += "采光通透，溢价空间大。" if '高' in str(t_floor) else "出行便利，稳定性好。"
            explanation += "\n"

        # Decoration
        t_deco = self._get_mapped_val(target_property, 'decoration')
        if t_deco:
            explanation += f"- **装修状况**: {t_deco}，"
            explanation += "具备显著溢价。" if '精' in str(t_deco) else "估值侧重房屋净值。"
            explanation += "\n"

        explanation += f"\n> **注**: 置信度基于案例相似度、市场波动及样本离散度综合判定。此结果仅供专业参考。"
        
        return explanation
        if 'fitment' in target_property:
            explanation += f"- 装修：目标房产装修状况为 {target_property['fitment']}，"
            if target_property['fitment'] == '精装' or target_property['fitment'] == 2:
                explanation += "精装修状况良好，对价格有明显正面影响。\n"
            elif target_property['fitment'] == '简装' or target_property['fitment'] == 1:
                explanation += "简单装修，对价格有一定正面影响。\n"
            else:
                explanation += "毛坯房，需要额外装修成本，对价格有一定负面影响。\n"
        
        # 分析房龄
        if 'age' in target_property:
            explanation += f"- 房龄：目标房产房龄为 {target_property['age']} 年，"
            if target_property['age'] < 5:
                explanation += "属于新房，对价格有正面影响。\n"
            elif target_property['age'] > 20:
                explanation += "房龄较长，可能需要维护，对价格有一定负面影响。\n"
            else:
                explanation += "房龄适中，对价格影响中性。\n"
        
        # 添加置信度解释
        explanation += f"\n估值置信度为 {confidence:.2%}，"
        if confidence > 0.8:
            explanation += "表示可比案例与目标房产高度相似，估值结果可靠性高。"
        elif confidence > 0.5:
            explanation += "表示可比案例与目标房产相似度适中，估值结果可靠性中等。"
        else:
            explanation += "表示可比案例与目标房产相似度较低，估值结果仅供参考。"
        
        return explanation 