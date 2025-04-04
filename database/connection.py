import psycopg2
from psycopg2.extras import DictCursor
from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from loguru import logger

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info("Подключение к PostgreSQL установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def get_connection(self):
        if self.conn is None or self.conn.closed:
            self.connect()
        return self.conn
    
    def execute_query(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute(query, params or ())
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
        finally:
            cursor.close()
    
    def fetch_all(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchall()
    
    def fetch_one(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchone()
    
    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            logger.info("Подключение к PostgreSQL закрыто")