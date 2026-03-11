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
        # 先在静态映射里找
        table = self.city_tables.get(city)
        if table: return table
        # 如果没找到，尝试拼音或查询数据库（这里简化为：如果没找到就查数据库或者直接返回None）
        # 实际项目中建议在数据库有一张映射表
        return None

    def get_all_cities_list(self):
        """获取所有已开设的城市列表"""
        try:
            query = "SELECT city_name FROM city"
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            return [r[0] for r in results]
        except mysql.connector.Error as err:
            print(f"获取城市列表失败: {err}")
            return ["上海", "北京"]

    def add_new_city(self, city_name, table_name, intro="", detail=""):
        """管理员：添加新城市并创建对应的数据表"""
        try:
            # 1. 写入 city 模型表
            query_city = "INSERT INTO city (city_name, city_introduction, detail) VALUES (%s, %s, %s)"
            self._cursor.execute(query_city, (city_name, intro, detail))
            
            # 2. 创建房产数据表 (基于上海表结构)
            query_create = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
              `id` int NOT NULL AUTO_INCREMENT,
              `house_type` text,
              `house_floor` text,
              `house_direction` text,
              `house_area` float DEFAULT NULL,
              `house_structure` text,
              `transaction_type` varchar(5) DEFAULT NULL,
              `transaction_time` text,
              `house_decoration` text,
              `is_elevator` varchar(3) DEFAULT NULL,
              `house_year` int DEFAULT NULL,
              `green_rate` text,
              `house_loc` text,
              `house_position` text,
              `u_price` float DEFAULT NULL,
              `t_price` int DEFAULT NULL,
              `detail_url` text,
              PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
            self._cursor.execute(query_create)
            self._connection.commit()
            
            # 动态更新映射
            MySQLManager.city_tables[city_name] = table_name
            return True
        except Exception as e:
            print(f"创建城市失败: {e}")
            if self._connection: self._connection.rollback()
            return False

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
                    try:
                        green_rate = float(green_rate_raw.strip('%')) / 100
                    except (ValueError, TypeError):
                        green_rate = 0.2
                elif green_rate_raw:
                    try:
                        val = float(green_rate_raw)
                        # 如果大于 1，一般是 35 这种表示 35%
                        if val > 1:
                            green_rate = val / 100
                        else:
                            green_rate = val
                    except (ValueError, TypeError):
                        green_rate = 0.2
                else:
                    green_rate = 0.2

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

    def init_users_table(self):
        """初始化用户表"""
        try:
            query = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
            self._cursor.execute(query)
            
            # 添加默认用户
            check_query = "SELECT COUNT(*) FROM users WHERE username='admin'"
            self._cursor.execute(check_query)
            if self._cursor.fetchone()[0] == 0:
                insert_query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
                self._cursor.execute(insert_query, ("admin", "admin@example.com", "123456"))
            
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"初始化用户表失败: {err}")
            return False

    def find_user(self, username_or_email):
        """查找用户"""
        try:
            query = "SELECT id, username, email, password FROM users WHERE username=%s OR email=%s"
            self._cursor.execute(query, (username_or_email, username_or_email))
            result = self._cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "password": result[3]
                }
            return None
        except mysql.connector.Error as err:
            print(f"查找用户失败: {err}")
            return None

    def create_user(self, username, email, password):
        """创建新用户"""
        try:
            query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
            self._cursor.execute(query, (username, email, password))
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"创建用户失败: {err}")
            return False

    def update_password(self, username, old_password, new_password):
        """更新用户密码"""
        try:
            # 首先验证旧密码
            query = "SELECT id FROM users WHERE username=%s AND password=%s"
            self._cursor.execute(query, (username, old_password))
            if not self._cursor.fetchone():
                return False, "当前密码错误"
            
            # 更新为新密码
            update_query = "UPDATE users SET password=%s WHERE username=%s"
            self._cursor.execute(update_query, (new_password, username))
            self._connection.commit()
            return True, "密码修改成功"
        except mysql.connector.Error as err:
            print(f"更新密码失败: {err}")
            return False, str(err)

    def init_reports_table(self):
        """初始化用户报告关联表"""
        try:
            query = """
            CREATE TABLE IF NOT EXISTS user_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                report_id VARCHAR(100) NOT NULL UNIQUE,
                address TEXT,
                city VARCHAR(50),
                area FLOAT,
                house_type TEXT,
                estimated_price FLOAT,
                total_price FLOAT,
                generated_at DATETIME,
                pdf_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
            self._cursor.execute(query)
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"初始化报告表失败: {err}")
            return False

    def save_user_report(self, report_data):
        """保存用户报告元数据到数据库"""
        try:
            query = """
            INSERT INTO user_reports (
                username, report_id, address, city, area, house_type, 
                estimated_price, total_price, generated_at, pdf_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                pdf_url = VALUES(pdf_url)
            """
            self._cursor.execute(query, (
                report_data.get('username'),
                report_data.get('report_id'),
                report_data.get('address'),
                report_data.get('city'),
                report_data.get('area'),
                report_data.get('house_type'),
                report_data.get('estimated_price'),
                report_data.get('total_price'),
                report_data.get('generated_at'),
                report_data.get('pdf_url')
            ))
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"保存报告元数据失败: {err}")
            return False

    def get_user_history(self, username):
        """获取指定用户的历史记录"""
        try:
            query = """
            SELECT report_id, address, city, area, house_type, estimated_price, total_price, generated_at, pdf_url
            FROM user_reports
            WHERE username = %s
            ORDER BY generated_at DESC
            """
            self._cursor.execute(query, (username,))
            results = self._cursor.fetchall()
            
            history = []
            for row in results:
                history.append({
                    'id': row[0],
                    'report_id': row[0],
                    'address': row[1],
                    'city': row[2],
                    'area': row[3],
                    'house_type': row[4],
                    'estimated_price': row[5],
                    'total_price': row[6],
                    'generated_at': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else '',
                    'pdf_url': row[8]
                })
            return history
        except mysql.connector.Error as err:
            print(f"获取用户历史失败: {err}")
            return []
            
    def update_report_pdf(self, report_id, pdf_url):
        """更新报告的 PDF URL"""
        try:
            query = "UPDATE user_reports SET pdf_url = %s WHERE report_id = %s"
            self._cursor.execute(query, (pdf_url, report_id))
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"更新报告PDF失败: {err}")
            return False

    def get_all_users(self):
        """管理员：获取所有用户"""
        try:
            query = "SELECT id, username, email, created_at FROM users WHERE username != 'admin'"
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            return [{"id": r[0], "username": r[1], "email": r[2], "created_at": r[3].strftime('%Y-%m-%d %H:%M:%S')} for r in results]
        except mysql.connector.Error as err:
            print(f"获取所有用户失败: {err}")
            return []

    def delete_user(self, username):
        """管理员：删除用户及其报告"""
        try:
            # 开启事务
            self._connection.start_transaction()
            # 删除用户的报告关联记录
            self._cursor.execute("DELETE FROM user_reports WHERE username = %s", (username,))
            # 删除用户账户
            self._cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            self._connection.rollback()
            print(f"删除用户失败: {err}")
            return False

    def get_all_reports(self):
        """管理员：查看系统中所有报告"""
        try:
            query = """
            SELECT report_id, username, address, city, total_price, generated_at, pdf_url 
            FROM user_reports 
            ORDER BY generated_at DESC
            """
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            return [{
                "report_id": r[0],
                "username": r[1],
                "address": r[2],
                "city": r[3],
                "total_price": r[4],
                "generated_at": r[5].strftime('%Y-%m-%d %H:%M:%S') if r[5] else '',
                "pdf_url": r[6]
            } for r in results]
        except mysql.connector.Error as err:
            print(f"获取所有报告失败: {err}")
            return []

    def delete_report(self, report_id):
        """管理员：删除报告记录"""
        try:
            query = "DELETE FROM user_reports WHERE report_id = %s"
            self._cursor.execute(query, (report_id,))
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"删除报告失败: {err}")
            return False

    def insert_manual_record(self, city, data):
        """管理员：手动添加房产成交数据到城市表"""
        table_name = self.get_table(city)
        if not table_name: return False
        try:
            query = f"""
            INSERT INTO {table_name} 
            (house_type, house_floor, house_direction, house_area, house_structure, 
             transaction_type, transaction_time, house_decoration, is_elevator, 
             house_year, green_rate, house_loc, house_position, u_price, t_price, detail_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                data.get('house_type'), data.get('house_floor'), data.get('house_direction'),
                data.get('house_area'), data.get('house_structure'), data.get('transaction_type', '普通成交'),
                data.get('transaction_time', datetime.datetime.now().strftime('%Y-%m-%d')),
                data.get('house_decoration'), data.get('is_elevator', 1),
                data.get('house_year'), data.get('green_rate', 30),
                data.get('house_loc'), data.get('house_position'),
                data.get('u_price'), data.get('t_price'), data.get('detail_url', '')
            )
            self._cursor.execute(query, values)
            self._connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"手动插入数据失败: {err}")
            return False


    @property
    def host(self):
        return self._host

