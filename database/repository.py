from loguru import logger
from datetime import datetime
from database.connection import Database

class WildberriesRepository:
    def __init__(self):
        self.db = Database()
    
    def save_product(self, product_data):
        """Сохраняет информацию о товаре в базу данных"""
        try:
            # Проверяем наличие бренда
            brand_id = self._get_or_create_brand(product_data['brand'])
            
            # Проверяем наличие категории
            category_id = self._get_or_create_category(product_data['category'])
            
            # Проверяем наличие продавца
            seller_id = self._get_or_create_seller(product_data['seller'])
            
            # Проверяем наличие товара в базе
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM products WHERE wb_id = %s",
                (product_data['wb_id'],)
            )
            product_row = cursor.fetchone()
            
            if product_row:
                # Обновляем существующий товар
                product_id = product_row[0]
                cursor.execute(
                    """
                    UPDATE products 
                    SET name = %s, brand_id = %s, category_id = %s, seller_id = %s,
                        rating = %s, feedbacks_count = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        product_data['name'], brand_id, category_id, seller_id,
                        product_data.get('rating'), product_data.get('feedbacks_count'),
                        datetime.now(), product_id
                    )
                )
            else:
                # Создаем новый товар
                cursor.execute(
                    """
                    INSERT INTO products 
                    (wb_id, name, brand_id, category_id, seller_id, rating, feedbacks_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        product_data['wb_id'], product_data['name'], brand_id, category_id, seller_id,
                        product_data.get('rating'), product_data.get('feedbacks_count'),
                        datetime.now(), datetime.now()
                    )
                )
                product_id = cursor.fetchone()[0]
            
            # Добавляем запись о цене
            cursor.execute(
                """
                INSERT INTO product_prices 
                (product_id, current_price, original_price, discount_percentage, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    product_id,
                    product_data['price'].get('current'),
                    product_data['price'].get('original'),
                    product_data['price'].get('discount_percentage'),
                    datetime.now()
                )
            )
            
            # Добавляем записи о наличии на складах
            for warehouse_id, quantity in product_data.get('stocks', {}).items():
                cursor.execute(
                    """
                    INSERT INTO product_stocks 
                    (product_id, warehouse_id, quantity, timestamp)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (product_id, warehouse_id, quantity, datetime.now())
                )
            
            conn.commit()
            cursor.close()
            
            logger.info(f"Товар с ID {product_data['wb_id']} успешно сохранен")
            return product_id
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении товара {product_data.get('wb_id')}: {e}")
            if 'conn' in locals() and 'cursor' in locals():
                conn.rollback()
                cursor.close()
            return None
    
    def _get_or_create_brand(self, brand_name):
        """Получает или создает бренд в базе данных"""
        query = "SELECT id FROM brands WHERE name = %s"
        brand_row = self.db.fetch_one(query, (brand_name,))
        
        if brand_row:
            return brand_row['id']
        
        # Создаем новый бренд
        query = "INSERT INTO brands (name, created_at, updated_at) VALUES (%s, %s, %s) RETURNING id"
        now = datetime.now()
        brand_row = self.db.fetch_one(query, (brand_name, now, now))
        
        return brand_row['id']
    
    def _get_or_create_category(self, category_name):
        """Получает или создает категорию в базе данных"""
        query = "SELECT id FROM categories WHERE name = %s"
        category_row = self.db.fetch_one(query, (category_name,))
        
        if category_row:
            return category_row['id']
        
        # Создаем новую категорию
        query = "INSERT INTO categories (name, created_at, updated_at) VALUES (%s, %s, %s) RETURNING id"
        now = datetime.now()
        category_row = self.db.fetch_one(query, (category_name, now, now))
        
        return category_row['id']
    
    def _get_or_create_seller(self, seller_data):
        """Получает или создает продавца в базе данных"""
        query = "SELECT id FROM sellers WHERE id = %s"
        seller_row = self.db.fetch_one(query, (seller_data['id'],))
        
        if seller_row:
            # Обновляем имя продавца, если оно изменилось
            query = "UPDATE sellers SET name = %s, updated_at = %s WHERE id = %s"
            self.db.execute_query(query, (seller_data['name'], datetime.now(), seller_data['id']))
            return seller_data['id']
        
        # Создаем нового продавца
        query = """
        INSERT INTO sellers (id, name, created_at, updated_at) 
        VALUES (%s, %s, %s, %s)
        """
        now = datetime.now()
        self.db.execute_query(query, (seller_data['id'], seller_data['name'], now, now))
        
        return seller_data['id']
    
    def save_feedback(self, product_id, feedback_data):
        """Сохраняет отзыв на товар"""
        try:
            # Проверяем наличие отзыва в базе
            query = """
            SELECT id FROM feedbacks 
            WHERE product_id = %s AND user_id = %s
            """
            
            feedback_row = self.db.fetch_one(query, (product_id, feedback_data.get('user_id')))
            
            if feedback_row:
                # Обновляем существующий отзыв
                query = """
                UPDATE feedbacks 
                SET rating = %s, text = %s, likes = %s, dislikes = %s, parsed_at = %s
                WHERE id = %s
                """
                
                self.db.execute_query(
                    query,
                    (
                        feedback_data.get('rating'),
                        feedback_data.get('text'),
                        feedback_data.get('likes', 0),
                        feedback_data.get('dislikes', 0),
                        datetime.now(),
                        feedback_row['id']
                    )
                )
                return feedback_row['id']
            else:
                # Создаем новый отзыв
                query = """
                INSERT INTO feedbacks 
                (product_id, user_id, rating, text, likes, dislikes, created_at, parsed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """
                
                created_at = None
                if feedback_data.get('created_timestamp'):
                    created_at = datetime.fromtimestamp(feedback_data.get('created_timestamp') / 1000)
                
                feedback_row = self.db.fetch_one(
                    query,
                    (
                        product_id,
                        feedback_data.get('user_id'),
                        feedback_data.get('rating'),
                        feedback_data.get('text'),
                        feedback_data.get('likes', 0),
                        feedback_data.get('dislikes', 0),
                        created_at,
                        datetime.now()
                    )
                )
                
                return feedback_row['id']
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении отзыва для товара {product_id}: {e}")
            return None
    
    def close(self):
        """Закрывает соединение с базой данных"""
        self.db.close()