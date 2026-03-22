from datetime import datetime, timedelta, date
from sqlalchemy import create_engine
import pandas as pd
import re
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import Dict, List, Any, Optional
import sys
import os

# 导入百度地图相关模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from record.save_map import get_origin_place


class careful_selection:
    """Class to handle careful selection of comparable properties for valuation."""
    
    # Pre-defined mappings for categorical distinctions
    FLOOR_MAP = {"低": 1, "中": 2, "高": 3}
    DECO_MAP = {"毛坯": 0, "简装": 1, "精装": 2}
    TYPE_PATTERN = re.compile(r'(\d+)室|(\d+)厅|(\d+)厨|(\d+)卫')

    def __init__(self, username, password, host, port, database, table, 
                 house_floor, house_area, house_type, house_decoration, 
                 house_year, house_loc, house_direction=None, house_structure=None,
                 selection_weights=None, city="上海"):
        self.table = table
        self.target_floor = self._get_floor_level(house_floor)
        self.target_area = float(house_area)
        self.target_type_vec = self._parse_house_type(house_type)
        self.target_decoration = self._get_deco_level(house_decoration)
        self.target_year = int(house_year)
        self.house_loc = house_loc
        self.city = city
        self.today = datetime.now()
        
        # 新增：朝向和结构
        self.target_direction = self._parse_direction(house_direction)
        self.target_structure = self._parse_structure(house_structure)
        
        # Original values kept for SQL queries if needed
        self.raw_house_floor = house_floor
        self.raw_house_type = house_type
        self.raw_house_decoration = house_decoration
        self.raw_house_year = house_year
        self.raw_house_area = house_area
        self.raw_house_direction = house_direction
        self.raw_house_structure = house_structure

        # Weights for distinction calculation
        self.weights = selection_weights or {
            'floor': 0.10,
            'area': 0.20,
            'type': 0.15,
            'decoration': 0.10,
            'year': 0.10,
            'time': 0.05,
            'direction': 0.15,  # 新增朝向权重
            'structure': 0.15   # 新增结构权重
        }

        uri = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
        self.engine = create_engine(uri)
        
        # 获取目标房产的经纬度
        self.target_lng = None
        self.target_lat = None
        self._init_target_location()

    def _init_target_location(self):
        """获取目标房产的经纬度"""
        try:
            # 清理地址
            clean_addr = re.sub(r'\d+[室层楼号弄]', '', str(self.house_loc))
            if not clean_addr:
                clean_addr = self.house_loc
            
            # 调用百度地图API
            result = get_origin_place(clean_addr, self.city, status=0)
            if result:
                self.target_lng, self.target_lat = result.split(',')
                self.target_lng = float(self.target_lng)
                self.target_lat = float(self.target_lat)
                print(f"目标房产位置: ({self.target_lng}, {self.target_lat})")
            else:
                print(f"警告: 无法获取目标房产 {clean_addr} 的位置")
        except Exception as e:
            print(f"获取目标位置失败: {e}")
    
    def _get_floor_level(self, floor_str: str) -> int:
        """Map floor description to numeric level."""
        for key, val in self.FLOOR_MAP.items():
            if key in str(floor_str):
                return val
        return 0

    def _get_deco_level(self, deco_str: str) -> int:
        """Map decoration description to numeric level."""
        return self.DECO_MAP.get(deco_str, 0)

    def _parse_house_type(self, type_str: str) -> np.ndarray:
        """Extract (Room, Hall, Kitchen, Bathroom) vector from string."""
        if not isinstance(type_str, str):
            return np.zeros(4)
        
        res = [0, 0, 0, 0]
        # More robust extraction
        matches = {
            '室': 0, '厅': 1, '厨': 2, '卫': 3
        }
        for label, idx in matches.items():
            m = re.search(rf'(\d+){label}', type_str)
            if m:
                res[idx] = int(m.group(1))
        return np.array(res)

    @staticmethod
    def trans_green_rate(s) -> float:
        if not isinstance(s, str):
            return 0.0
        f = re.findall(r'\d+\.?\d*', s)
        if "%" in s and f:
            return float(f[0]) / 100
        return 0.0

    def _filter_outlier_prices(self, df: pd.DataFrame, threshold: float = 0.30) -> pd.DataFrame:
        """过滤价格异常值（过高或过低）
        
        使用价格中位数作为基准，过滤掉 ±threshold 范围外的案例
        如果过滤后案例不足3个，则保留原始数据
        """
        try:
            prices = df['u_price'].dropna()
            if len(prices) < 3:
                return df
            
            median_price = prices.median()
            lower_bound = median_price * (1 - threshold)
            upper_bound = median_price * (1 + threshold)
            
            original_count = len(df)
            df_filtered = df[(df['u_price'] >= lower_bound) & (df['u_price'] <= upper_bound)]
            
            # 如果过滤后不足3个案例，回退到原始数据
            if len(df_filtered) < 3:
                print(f"价格过滤后案例不足，回退到原始数据（过滤前 {original_count} 条）")
                return df
            
            filtered_count = len(df_filtered)
            print(f"价格过滤完成：{original_count} -> {filtered_count} 条，范围: {lower_bound:.0f} ~ {upper_bound:.0f}")
            return df_filtered
            
        except Exception as e:
            print(f"价格过滤失败: {e}")
            return df

    @staticmethod
    def _parse_direction(direction_str) -> int:
        """解析朝向，返回价值评分（越高越好）
        南北通透 > 南 > 东南/西南 > 东/西 > 北
        """
        if not direction_str:
            return 3  # 默认中等
        
        direction_str = str(direction_str).upper()
        
        # 南北通透最好
        if '南' in direction_str and '北' in direction_str:
            return 5
        # 纯南
        if '南' in direction_str:
            return 4
        # 东南/西南
        if '东南' in direction_str or '西南' in direction_str:
            return 3
        # 纯东/纯西
        if '东' in direction_str or '西' in direction_str:
            return 2
        # 北向最差
        if '北' in direction_str:
            return 1
        return 3

    @staticmethod
    def _parse_structure(structure_str) -> int:
        """解析建筑结构，返回价值评分（越高越好）
        别墅 > 复式 > 平层
        """
        if not structure_str:
            return 2  # 默认平层
        
        structure_str = str(structure_str)
        
        if '别墅' in structure_str:
            return 3
        if '复式' in structure_str or '跃层' in structure_str:
            return 2
        if '平层' in structure_str:
            return 1
        return 1

    def selection(self) -> List[Dict[str, Any]]:
        """Main selection logic with tiered strategy and vectorized distance calculation."""
        try:
            # 1. Tiered Retrieval Strategy
            base_loc = self.house_loc.split('(')[0] if self.house_loc else ""
            df = self._retrieve_data(base_loc)
            
            if df.empty:
                print("No comparable cases found after all strategies.")
                return []
            
            # 2. Vectorized Cleaning and Pre-processing
            # Remove "Unknown" or "N/A" values for critical features
            mask = ~df[['house_floor', 'house_area', 'house_type', 'house_decoration', 'house_year']].astype(str).apply(
                lambda x: x.str.contains('暂无数据|未知|None|nan', case=False)
            ).any(axis=1)
            df = df[mask].copy()
            
            if df.empty:
                print("No valid cases remaining after data cleaning.")
                return []

            # 3. Calculate Normalized Distances (Distinction)
            # Use vectorized operations where possible for performance
            df['d_floor'] = df['house_floor'].apply(self._get_floor_level).apply(
                lambda x: abs(x - self.target_floor) if x and self.target_floor else 3
            )
            df['d_area'] = (df['house_area'].astype(float) - self.target_area).abs()
            
            # Type vector distance - 优化：不同房间类型不同权重
            # 室 > 厅 > 卫 > 厨
            def calc_type_distance(type_str):
                vec = self._parse_house_type(type_str)
                target = self.target_type_vec
                # 权重: 室=0.4, 厅=0.3, 厨=0.1, 卫=0.2
                weights = np.array([0.4, 0.3, 0.1, 0.2])
                return np.sum(np.abs(vec - target) * weights)
            df['d_type'] = df['house_type'].apply(calc_type_distance)
            
            df['d_deco'] = df['house_decoration'].apply(self._get_deco_level).apply(
                lambda x: abs(x - self.target_decoration)
            )
            
            df['d_year'] = pd.to_numeric(df['house_year'], errors='coerce').fillna(self.target_year).apply(
                lambda x: abs(int(x) - self.target_year)
            )
            
            # Time distance in days
            df['d_time'] = pd.to_datetime(df['transaction_time'], errors='coerce').apply(
                lambda x: abs((self.today - x).days) if pd.notnull(x) else 365
            )
            
            # 新增：朝向距离（差异越大扣分越多）
            df['d_direction'] = df['house_direction'].apply(
                lambda x: abs(self._parse_direction(x) - self.target_direction)
            )
            
            # 新增：结构距离
            df['d_structure'] = df['house_structure'].apply(
                lambda x: abs(self._parse_structure(x) - self.target_structure)
            )

            # 4. Scaling and Weighting
            cols = ['d_floor', 'd_area', 'd_type', 'd_deco', 'd_year', 'd_time', 'd_direction', 'd_structure']
            scaler = MinMaxScaler()
            df[cols] = scaler.fit_transform(df[cols])
            
            df['distinction'] = (
                self.weights['floor'] * df['d_floor'] +
                self.weights['area'] * df['d_area'] +
                self.weights['type'] * df['d_type'] +
                self.weights['decoration'] * df['d_deco'] +
                self.weights['year'] * df['d_year'] +
                self.weights['time'] * df['d_time'] +
                self.weights['direction'] * df['d_direction'] +
                self.weights['structure'] * df['d_structure']
            )

            # Cleanup and sort
            if 'green_rate' in df.columns:
                df['green_rate'] = df['green_rate'].apply(self.trans_green_rate)
            
            # 先取5个案例
            top5 = df.sort_values('distinction').head(5)
            
            # ===== 价格异常过滤（对5个案例） =====
            if 'u_price' in top5.columns and len(top5) >= 3:
                top5 = self._filter_outlier_prices(top5)
            
            return top5.to_dict(orient='records')

        except Exception as e:
            print(f"Error in careful selection: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _retrieve_data(self, base_loc: str) -> pd.DataFrame:
        """Implements the multi-level search strategy with location-based filtering."""
        
        # 成交时间筛选：只取2025年1月1日之后的数据
        min_transaction_date = "2025-01-01"
        
        # 如果有目标经纬度，使用基于距离的检索
        if self.target_lng and self.target_lat:
            # Haversine公式计算距离的SQL (单位：公里)
            distance_sql = f"""
                (6371 * acos(cos(radians({self.target_lat})) * cos(radians(lat)) 
                * cos(radians(lng) - radians({self.target_lng})) 
                + sin(radians({self.target_lat})) * sin(radians(lat)))) AS distance
            """
            
            strategies = [
                # T1: 同一小区 + 严格条件 (1公里内)
                {"sql": f"""SELECT *, {distance_sql} FROM {self.table} 
                    WHERE house_loc LIKE '%{base_loc}%' 
                    AND ABS(house_area - {self.target_area}) <= {self.target_area * 0.15} 
                    AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 5
                    AND transaction_time >= '{min_transaction_date}'
                    HAVING distance <= 1""", "max_dist": 1},
                
                # T2: 2公里内 + 中等条件
                {"sql": f"""SELECT *, {distance_sql} FROM {self.table} 
                    WHERE lng IS NOT NULL AND lat IS NOT NULL 
                    AND ABS(house_area - {self.target_area}) <= {self.target_area * 0.25}
                    AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 8
                    AND transaction_time >= '{min_transaction_date}'
                    HAVING distance <= 2""", "max_dist": 2},
                
                # T3: 3公里内 + 放宽条件
                {"sql": f"""SELECT *, {distance_sql} FROM {self.table} 
                    WHERE lng IS NOT NULL AND lat IS NOT NULL
                    AND ABS(house_area - {self.target_area}) <= 50
                    AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 15
                    AND transaction_time >= '{min_transaction_date}'
                    HAVING distance <= 3""", "max_dist": 3},
            ]
        else:
            # 没有经纬度时使用原有逻辑
            print("警告: 无目标经纬度，使用传统检索方式")
            strategies = [
                {"sql": f"SELECT * FROM {self.table} WHERE house_loc LIKE '%{base_loc}%' AND ABS(house_area - {self.target_area}) <= {self.target_area * 0.15} AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 5 AND transaction_time >= '{min_transaction_date}'"},
                {"sql": f"SELECT * FROM {self.table} WHERE house_loc LIKE '%{base_loc}%' AND ABS(house_area - {self.target_area}) <= {self.target_area * 0.3} AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 10 AND transaction_time >= '{min_transaction_date}'"},
                {"sql": f"SELECT * FROM {self.table} WHERE ABS(house_area - {self.target_area}) <= 50 AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 15 AND transaction_time >= '{min_transaction_date}'"}
            ]
        
        for strategy in strategies:
            try:
                df = pd.read_sql(strategy['sql'], self.engine)
                if len(df) >= 3:
                    if 'distance' in df.columns:
                        df = df.sort_values('distance')
                        max_dist = strategy.get('max_dist', '未知')
                        print(f"检索到 {len(df)} 条案例，范围: {max_dist}公里内")
                    return df
            except Exception as e:
                print(f"SQL执行失败: {e}")
                continue
        
        # 兜底策略：返回有经纬度的最近案例
        if self.target_lng and self.target_lat:
            try:
                distance_sql = f"""
                    (6371 * acos(cos(radians({self.target_lat})) * cos(radians(lat)) 
                    * cos(radians(lng) - radians({self.target_lng})) 
                    + sin(radians({self.target_lat})) * sin(radians(lat)))) AS distance
                """
                df = pd.read_sql(f"""SELECT *, {distance_sql} FROM {self.table} 
                    WHERE lng IS NOT NULL AND lat IS NOT NULL
                    AND transaction_time >= '{min_transaction_date}'
                    ORDER BY distance LIMIT 20""", self.engine)
                if len(df) >= 3:
                    print(f"使用兜底策略检索到 {len(df)} 条案例")
                    return df
            except Exception as e:
                print(f"兜底查询也失败: {e}")
        
        return pd.DataFrame()
