import sqlite3
from datetime import datetime


class SQLite:

    def __init__(self, db_file_path: str):
        self.conn = sqlite3.connect(db_file_path)
        self.cursor = self.conn.cursor()

    def create_table_if_not_exists(self, table_name: str):
        self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS "{table_name}" (
    ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL DEFAULT 1,
    price REAL NOT NULL,
    timestamp TEXT NOT NULL
    )''')
        self.conn.commit()

    def insert_data(self, table: str, price: float, timestamp: datetime = datetime.now()):
        self.create_table_if_not_exists(table)
        datetime_str = timestamp.strftime('%d/%m/%Y %H:%M')
        self.cursor.execute(f'''INSERT INTO "{table}" (price, timestamp) VALUES ({price}, "{datetime_str}")''')
        self.conn.commit()

    def reset_auto_increment(self, table: str):
        self.cursor.execute(f'UPDATE SQLITE_SEQUENCE SET SEQ=0 WHERE NAME="{table}"')
        self.conn.commit()