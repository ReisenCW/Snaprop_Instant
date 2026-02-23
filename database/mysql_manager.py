"""
本模块包含 MySQL管理 类
"""
import mysql.connector
import pandas as pd
import datetime
from config.mysql_config import mysql_host, mysql_db, mysql_port, mysql_username, mysql_password


class MySQLManager():
    """
    MySQL数据库管理 类
    """
    city_tables = {"上海": "shanghai",
                   "北京": "beijing"
                   }

    def __init__(self):
        self._host = mysql_host
        self._port = mysql_port
        self._username = mysql_username
        self._password = mysql_password
        self._db = mysql_db
        self._connection = None
        self._cursor = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        try:
            if self._connection and self._connection.is_connected():
                return
            self._connection = mysql.connector.connect(
                host=self._host,
                port=self._port,
                user=self._username,
                password=self._password,
                database=self._db
            )
            self._cursor = self._connection.cursor()
        except mysql.connector.Error as err:
            print(f"数据库连接失败: {err}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭数据库资源"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._connection:
            if self._connection.is_connected():
                self._connection.close()
            self._connection = None

    def get_cursor(self):
        """获取游标，确保连接处于活动状态"""
        self._connect()
        return self._cursor

    def get_table(self, city):
        return self.city_tables.get(city)

    def insert(self, city, filepath):
        """
        批量插入城市房产数据
        """
        table_name = self.get_table(city)
        if not table_name:
            print(f"未知城市: {city}")
            return

        try:
            df = pd.read_excel(filepath)
            # 处理日期格式
            if 'transaction_time' in df.columns:
                df['transaction_time'] = pd.to_datetime(df['transaction_time']).dt.strftime('%Y-%m-%d')
            
            # 处理 NaN 和 空字符串
            df = df.where(pd.notnull(df), None)
            df.replace('未知', None, inplace=True)
            df.replace('', None, inplace=True)

            # 插入查询
            insert_query = f"""
            INSERT INTO {table_name} 
            (house_type, house_floor, house_direction, house_area, house_structure, 
             transaction_type, transaction_time, house_decoration, is_elevator, 
             house_year, green_rate, house_loc, house_position, u_price, t_price, detail_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 准备数据元组列表
            data_to_insert = [
                (
                    row['house_type'], row['house_floor'], row['house_direction'], row['house_area'],
                    row['house_structure'], row['transaction_type'], row['transaction_time'], row['house_decoration'],
                    row['is_elevator'], row['house_year'], row['green_rate'], row['house_loc'], row['house_position'],
                    row['u_price'], row['t_price'], row['detail_url']
                ) for _, row in df.iterrows()
            ]

            # 批量执行
            self._cursor.executemany(insert_query, data_to_insert)
            self._connection.commit()
            print(f"数据插入完成！共计 {len(data_to_insert)} 条数据。")

        except Exception as err:
            if self._connection:
                self._connection.rollback()
            print(f"数据插入失败: {err}")

    def get_city_info(self, city):
        """
        获取城市信息（合并查询优化）
        """
        try:
            query = "SELECT city_introduction, detail FROM city WHERE city_name=%s"
            self._cursor.execute(query, (city,))
            result = self._cursor.fetchone()
            
            if result:
                return result[0], result[1]
            return None, None
            
        except mysql.connector.Error as err:
            print(f"获取城市信息失败: {err}")
            return None, None

    def get_comparable_cases(self, city, limit=10):
        """
        获取可比案例数据，优化性能和默认值处理
        """
        table_name = self.get_table(city)
        if not table_name:
            return []

        try:
            query = f"""
            SELECT u_price, house_area, house_floor, house_decoration, house_year, 
                   transaction_time, green_rate, house_loc
            FROM {table_name} 
            WHERE u_price IS NOT NULL AND house_area IS NOT NULL
            ORDER BY transaction_time DESC 
            LIMIT %s
            """
            self._cursor.execute(query, (limit,))
            results = self._cursor.fetchall()
            
            comparable_cases = []
            for row in results:
                # 解析 green_rate，处理可能出现的百分号或 None
                green_rate_raw = row[6]
                if isinstance(green_rate_raw, str) and '%' in green_rate_raw:
                    green_rate = float(green_rate_raw.strip('%')) / 100
                elif green_rate_raw:
                    try:
                        green_rate = float(green_rate_raw)
                    except (ValueError, TypeError):
                        green_rate = 0.3
                else:
                    green_rate = 0.3

                case = {
                    'price': float(row[0]) if row[0] is not None else 0.0,
                    'size': float(row[1]) if row[1] is not None else 0.0,
                    'floor': row[2] if row[2] else '中楼层',
                    'fitment': row[3] if row[3] else '简装',
                    'built_time': str(row[4]) if row[4] else "2015",
                    'transaction_time': str(row[5]) if row[5] else "2023",
                    'green_rate': green_rate,
                    'address': row[7] if row[7] else '未知地址',
                    'transaction_type': 1
                }
                comparable_cases.append(case)
            
            return comparable_cases
        except mysql.connector.Error as err:
            print(f"获取可比案例失败: {err}")
            return []


    @property
    def host(self):
        return self._host

