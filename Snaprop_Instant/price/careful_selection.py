from datetime import datetime, timedelta, date
from sqlalchemy import create_engine
import pandas as pd
import re
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import Dict, List, Any, Optional


class careful_selection:
    """Class to handle careful selection of comparable properties for valuation."""
    
    # Pre-defined mappings for categorical distinctions
    FLOOR_MAP = {"低": 1, "中": 2, "高": 3}
    DECO_MAP = {"毛坯": 0, "简装": 1, "精装": 2}
    TYPE_PATTERN = re.compile(r'(\d+)室|(\d+)厅|(\d+)厨|(\d+)卫')

    def __init__(self, username, password, host, port, database, table, 
                 house_floor, house_area, house_type, house_decoration, 
                 house_year, house_loc, selection_weights=None):
        self.table = table
        self.target_floor = self._get_floor_level(house_floor)
        self.target_area = float(house_area)
        self.target_type_vec = self._parse_house_type(house_type)
        self.target_decoration = self._get_deco_level(house_decoration)
        self.target_year = int(house_year)
        self.house_loc = house_loc
        self.today = datetime.now()
        
        # Original values kept for SQL queries if needed
        self.raw_house_floor = house_floor
        self.raw_house_type = house_type
        self.raw_house_decoration = house_decoration
        self.raw_house_year = house_year
        self.raw_house_area = house_area

        # Weights for distinction calculation
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
            
            # Type vector distance
            df['d_type'] = df['house_type'].apply(lambda x: np.sum(np.abs(self._parse_house_type(x) - self.target_type_vec)))
            
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

            # 4. Scaling and Weighting
            cols = ['d_floor', 'd_area', 'd_type', 'd_deco', 'd_year', 'd_time']
            scaler = MinMaxScaler()
            df[cols] = scaler.fit_transform(df[cols])
            
            df['distinction'] = (
                self.weights['floor'] * df['d_floor'] +
                self.weights['area'] * df['d_area'] +
                self.weights['type'] * df['d_type'] +
                self.weights['decoration'] * df['d_deco'] +
                self.weights['year'] * df['d_year'] +
                self.weights['time'] * df['d_time']
            )

            # Cleanup and sort
            if 'green_rate' in df.columns:
                df['green_rate'] = df['green_rate'].apply(self.trans_green_rate)
            
            return df.sort_values('distinction').head(5).to_dict(orient='records')

        except Exception as e:
            print(f"Error in careful selection: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _retrieve_data(self, base_loc: str) -> pd.DataFrame:
        """Implements the multi-level search strategy."""
        strategies = [
            # T1: Same community, tight constraints
            {"sql": f"SELECT * FROM {self.table} WHERE house_loc LIKE '%%{base_loc}%%' AND ABS(house_area - {self.target_area}) <= {self.target_area * 0.15} AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 5"},
            # T2: Same community, relaxed constraints
            {"sql": f"SELECT * FROM {self.table} WHERE house_loc LIKE '%%{base_loc}%%' AND ABS(house_area - {self.target_area}) <= {self.target_area * 0.3} AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 10"},
            # T3: Neighborhood/Wider area (if base_loc is specific)
            {"sql": f"SELECT * FROM {self.table} WHERE ABS(house_area - {self.target_area}) <= 50 AND ABS(CAST(house_year AS SIGNED) - {self.target_year}) <= 15"}
        ]
        
        for strategy in strategies:
            try:
                df = pd.read_sql(strategy['sql'], self.engine)
                if len(df) >= 3:
                    return df
            except Exception:
                continue
        return pd.DataFrame()
