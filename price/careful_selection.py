from datetime import datetime, timedelta
from sqlalchemy import create_engine
import pandas as pd
import re
import time
from sklearn.preprocessing import MinMaxScaler
import numpy as np


class careful_selection:
    def __init__(self, username, password, host, port, database, table, house_floor, house_area, house_type,
                 house_decoration, house_year, house_loc, selection_weights=None):
        self.table = table
        self.house_floor = house_floor
        self.house_area = house_area
        self.house_type = house_type
        self.house_decoration = house_decoration
        self.house_year = house_year
        self.house_loc = house_loc
        self.today = time.strftime("%Y-%m-%d", time.localtime())
        
        # 默认权重
        self.weights = selection_weights or {
            'floor': 0.15,
            'area': 0.25,
            'type': 0.20,
            'decoration': 0.15,
            'year': 0.15,
            'time': 0.10
        }

        uri = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
        self.engine = create_engine(uri)
        
    @staticmethod
    def trans_green_rate(s) -> float:
        if not isinstance(s, str):
            return 0
        f = re.findall(r'\d+', s)
        if "%" in s and f:
            return int(f[0]) / 100
        return 0

    def house_floor_distinction(self, floor1, floor2):
        if "低" in floor1:
            floor1 = "低"
        elif "中" in floor1:
            floor1 = "中"
        elif "高" in floor1:
            floor1 = "高"
        if "低" in floor2:
            floor2 = "低"
        elif "中" in floor2:
            floor2 = "中"
        elif "高" in floor2:
            floor2 = "高"

        if (floor1 == "低" and floor2 == "低") or (floor1 == "中" and floor2 == "中") or (
                floor1 == "高" and floor2 == "高"):
            return 0
        elif (floor1 == "低" and floor2 == "中") or (floor1 == "中" and floor2 == "低") or (
                floor1 == "中" and floor2 == "高") or (floor1 == "高" and floor2 == "中"):
            return 1
        elif (floor1 == "低" and floor2 == "高") or (floor1 == "高" and floor2 == "低"):
            return 2
        return 3

    def house_area_distinction(self, area1, area2):
        return abs(area1 - area2)

    def house_type_distinction(self, type1, type2):
        w_room = 1
        w_hall = 1
        w_bathroom = 1
        w_kitchen = 1

        pattern = r'(\d+)室(\d+)厅(\d+)厨(\d+)卫'
        match1 = re.search(pattern, type1)
        match2 = re.search(pattern, type2)
        
        if not match1 or not match2:
            # 如果格式不匹配，返回最大差异
            return 10
        
        room1, hall1, kitchen1, bathroom1 = int(match1.group(1)), int(match1.group(2)), int(match1.group(3)), int(match1.group(4))
        room2, hall2, kitchen2, bathroom2 = int(match2.group(1)), int(match2.group(2)), int(match2.group(3)), int(match2.group(4))
        return w_room * abs(room1 - room2) + w_hall * abs(hall1 - hall2) + w_bathroom * abs(bathroom1 - bathroom2) + w_kitchen * abs(kitchen1 - kitchen2)

    def house_decorating_distinction(self, decoration1, decoration2):
        if (decoration1 == "毛坯" and decoration2 == "毛坯") or (decoration1 == "简装" and decoration2 == "简装") or (
                decoration1 == "精装" and decoration2 == "精装"):
            return 0
        elif (decoration1 == "毛坯" and decoration2 == "简装") or (decoration1 == "简装" and decoration2 == "毛坯") or (
                decoration1 == "简装" and decoration2 == "精装") or (decoration1 == "精装" and decoration2 == "简装"):
            return 1
        elif (decoration1 == "毛坯" and decoration2 == "精装") or (decoration1 == "精装" and decoration2 == "毛坯"):
            return 2
        return 3

    def house_year_distinction(self, year1, year2):
        return abs(int(year1) - int(year2))

    def transaction_time_distinction(self, date1, date2):
        date1 = datetime.strptime(date1, "%Y-%m-%d")
        date2 = datetime.strptime(date2, "%Y-%m-%d")
        return abs(date1 - date2).days

    def selction(self) -> list:
        try:
            # 基础小区名处理（去除括号内容，如"仁恒森兰雅苑(一期)" -> "仁恒森兰雅苑"）
            base_loc = self.house_loc.split('(')[0] if self.house_loc else ""
            
            # 定义分级筛选策略
            strategies = [
                # Level 1: 精确匹配 (同小区, 面积差异<15%, 房龄差异<5年)
                {
                    "name": "精确匹配",
                    "area_diff_ratio": 0.15,
                    "year_diff": 5,
                    "loc_strict": True
                },
                # Level 2: 同小区宽泛匹配 (同小区, 面积差异<30%, 房龄差异<10年)
                {
                    "name": "同小区宽泛匹配",
                    "area_diff_ratio": 0.30,
                    "year_diff": 10,
                    "loc_strict": True
                },
                # Level 3: 兜底匹配 (地址模糊匹配, 面积差异<50平米, 房龄差异<15年)
                {
                    "name": "兜底匹配",
                    "area_diff_fixed": 50,
                    "year_diff": 15,
                    "loc_strict": False
                }
            ]
            
            df = pd.DataFrame()
            
            for strategy in strategies:
                # print(f"尝试筛选策略: {strategy['name']}...")
                
                conditions = []
                
                # 1. 地址条件
                if strategy['loc_strict']:
                    if base_loc:
                        # 精确模式：必须包含小区名
                        conditions.append(f"house_loc LIKE '%%{base_loc}%%'")
                    else:
                        conditions.append("1=1")
                else:
                    # 宽松模式：如果不强求小区匹配，完全忽略地址，让其他条件生效
                    conditions.append("1=1")
                
                # 2. 房龄条件
                conditions.append(f"ABS(CAST(house_year AS SIGNED) - {self.house_year}) <= {strategy['year_diff']}")
                
                # 3. 面积条件
                if 'area_diff_ratio' in strategy:
                    area_diff = float(self.house_area) * strategy['area_diff_ratio']
                    conditions.append(f"ABS(house_area - {self.house_area}) <= {area_diff}")
                else:
                    conditions.append(f"ABS(house_area - {self.house_area}) <= {strategy['area_diff_fixed']}")
                
                where_clause = " AND ".join(conditions)
                query = f"SELECT * FROM {self.table} WHERE {where_clause}"
                
                temp_df = pd.read_sql(query, self.engine)
                
                # 如果找到足够数量的案例（例如至少3个），则停止
                if not temp_df.empty and len(temp_df) >= 3:
                    df = temp_df
                    print(f"策略 [{strategy['name']}] 成功，找到 {len(df)} 个案例")
                    break
            
            if df.empty:
                print("所有策略均未找到符合条件的案例")
                return []
            
            # 数据清理
            features = ['house_floor', 'house_area', 'house_type', 'house_decoration', 'house_year', 'transaction_time']
            df = df[~df[features].apply(lambda row: row.astype(str).str.contains('暂无数据|未知')).any(axis=1)]
            
            if df.empty:
                print("数据清理后没有有效案例")
                return []
            
            df['house_year'] = df['house_year'].replace('未知', np.nan)
            if not df['house_year'].dropna().empty:
                mean_value = int(df['house_year'].dropna().astype(int).mean())
                df['house_year'] = df['house_year'].replace(np.nan, mean_value)
            df['house_year'] = df['house_year'].astype(int)
            
            # 计算区别度
            df['house_floor_distinction'] = df['house_floor'].apply(
                lambda x: self.house_floor_distinction(x, self.house_floor))
            df['house_area_distinction'] = df['house_area'].apply(
                lambda x: self.house_area_distinction(x, float(self.house_area)))
            df['house_type_distinction'] = df['house_type'].apply(
                lambda x: self.house_type_distinction(x, self.house_type))
            df['house_decorating_distinction'] = df['house_decoration'].apply(
                lambda x: self.house_decorating_distinction(x, self.house_decoration))
            df['house_year_distinction'] = df['house_year'].apply(
                lambda x: self.house_year_distinction(x, int(self.house_year)))
            df['transaction_time_distinction'] = df['transaction_time'].apply(
                lambda x: self.transaction_time_distinction(x, self.today))

            # 标准化
            scaler = MinMaxScaler()
            columns_to_scale = ['house_floor_distinction', 'house_area_distinction', 'house_type_distinction',
                                'house_decorating_distinction', 'house_year_distinction',
                                'transaction_time_distinction']
            if not df.empty:
                scaled_data = scaler.fit_transform(df[columns_to_scale])
                df[columns_to_scale] = scaled_data
            
            # 加权综合区别度
            df['distinction'] = (
                self.weights['floor'] * df['house_floor_distinction'] +
                self.weights['area'] * df['house_area_distinction'] +
                self.weights['type'] * df['house_type_distinction'] +
                self.weights['decoration'] * df['house_decorating_distinction'] +
                self.weights['year'] * df['house_year_distinction'] +
                self.weights['time'] * df['transaction_time_distinction']
            )
            
            # 转换绿化率
            if 'green_rate' in df.columns:
                df['green_rate'] = df['green_rate'].apply(self.trans_green_rate)

            df = df.sort_values(by='distinction')
            
            return df[:5].to_dict(orient='records')
        
        except Exception as e:
            print(f"精筛过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
