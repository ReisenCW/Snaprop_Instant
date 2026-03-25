# MySQL数据库配置
import os

# 优先使用环境变量（Docker部署时）
# 否则使用本地配置
mysql_host = os.getenv("MYSQL_HOST", "localhost")
mysql_db = os.getenv("MYSQL_DATABASE", "house")
mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
mysql_username = os.getenv("MYSQL_USER", "root")
mysql_password = os.getenv("MYSQL_PASSWORD", "050117")
