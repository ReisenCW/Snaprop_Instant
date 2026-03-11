from database.mysql_manager import MySQLManager

def init_tables():
    try:
        db = MySQLManager()
        if db.init_users_table():
            print("Users table checked/initialized.")
        if db.init_reports_table():
            print("User reports table checked/initialized.")
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_tables()
