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
        self._connection = mysql.connector.connect(
            host=self._host,
            port=self._port,
            user=self._username,
            password=self._password,
            database=self._db
        )
        self._cursor = self._connection.cursor()

    def close(self):
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()

    def get_cursor(self):
        self._connection = mysql.connector.connect(
            host=self._host,
            port=self._port,
            user=self._username,
            password=self._password,
            database=self._db
        )
        self._cursor = self._connection.cursor()
        return self._cursor

    def get_table(self, city):
        table_name = self.city_tables[city]
        return table_name

    def insert(self, city, filepath):
        table_name = self.get_table(city)
        df = pd.read_excel(filepath)
        insert_query = f"""
        INSERT INTO {table_name} (house_type,house_floor,house_direction,house_area,house_structure,transaction_type,transaction_time,house_decoration,is_elevator,house_year,green_rate,house_loc,house_position,u_price,t_price,detail_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s, %s)
        """
        df['transaction_time'] = pd.to_datetime(df['transaction_time']).dt.strftime('%Y-%m-%d')
        for _, row in df.iterrows():
            try:
                house_year = row['house_year']
                if pd.isna(house_year) or str(house_year).strip() in ['未知', '']:
                    house_year = None

                self._cursor.execute(insert_query, (
                    row['house_type'], row['house_floor'], row['house_direction'], row['house_area'],
                    row['house_structure'], row['transaction_type'], row['transaction_time'], row['house_decoration'],
                    row['is_elevator'], house_year, row['green_rate'], row['house_loc'], row['house_position'],
                    row['u_price'], row['t_price'], row['detail_url']))
                self._connection.commit()  # 提交事务
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                self._connection.rollback()  # 回滚事务
        print("数据插入完成！")

    def get_city_info(self, city):
        try:
            introduction_query="SELECT city_introduction FROM city WHERE city_name=%s"
            self._cursor.execute(introduction_query, (city,))
            introduction = self._cursor.fetchone()
            detail_query="SELECT detail FROM city WHERE city_name=%s"
            self._cursor.execute(detail_query, (city,))
            detail = self._cursor.fetchone()
            return introduction[0], detail[0]
        except mysql.connector.Error as err:
            print(f"Error: {err}")

    def get_comparable_cases(self, city, limit=10):
        """
        获取可比案例数据
        
        Args:
            city: 城市名
            limit: 返回记录数量限制
            
        Returns:
            list: 可比案例列表
        """
        try:
            table_name = self.get_table(city)
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
                case = {
                    'price': float(row[0]),  # u_price
                    'size': float(row[1]),   # house_area
                    'floor': row[2] if row[2] else '中楼层',  # house_floor
                    'fitment': row[3] if row[3] else '简装',   # house_decoration
                    'built_time': f"{row[4]}-01-01" if row[4] else "2015",  # house_year
                    'transaction_time': str(row[5]) if row[5] else "2023",  # transaction_time
                    'green_rate': float(row[6].strip('%')) / 100 if row[6] and '%' in row[6] else (float(row[6]) if row[6] else 0.3),  # green_rate
                    'address': row[7] if row[7] else '未知地址',  # house_loc
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


if __name__ == '__main__':
    mysql_manager = MySQLManager()

    # print(mysql_manager.get_table("上海"))

    filepath = "D:/sitp_work/data/森兰明轩.xlsx"
    mysql_manager.insert("上海", filepath)

    # mysql_manager.get_city_info("上海")
