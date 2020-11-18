import sqlite3
from datetime import datetime
from typing import Union, Tuple


class SQLite:

    def __init__(self, db_file_path: str):
        self.conn = sqlite3.connect(db_file_path)
        self.cursor = self.conn.cursor()

    def create_table_if_not_exists(self, table_name: str):
        query = f'''CREATE TABLE IF NOT EXISTS "{table_name}" (
    ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL DEFAULT 1,
    price REAL NOT NULL,
    timestamp TEXT NOT NULL)'''
        self.cursor.execute(query)
        self.conn.commit()

    def insert_data(self, table: str, price: float, timestamp: datetime = datetime.now()):
        self.create_table_if_not_exists(table)
        datetime_str = timestamp.strftime('%d/%m/%Y %H:%M')
        query = f'INSERT INTO "{table}" (price, timestamp) VALUES (?, ?)'
        self.cursor.execute(query, (price, datetime_str))
        self.conn.commit()

    def reset_auto_increment(self, table: str):
        query = 'UPDATE SQLITE_SEQUENCE SET SEQ=0 WHERE NAME=?'
        self.cursor.execute(query, (table,))
        self.conn.commit()

    def is_lower_than_table_min(self, table: str, value: float,
                                column: str = 'price') -> Union[bool, Tuple[bool, float]]:
        query = f'SELECT MIN({column}) FROM "{table}"'
        self.cursor.execute(query)
        result = self.cursor.fetchone()[0]

        if t := value < result:
            return t, result
        else:
            return t
