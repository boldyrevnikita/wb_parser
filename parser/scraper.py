import requests
import json
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from config.settings import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, USER_AGENTS
from parser.anti_block import get_random_user_agent, get_random_delay, exponential_backoff

class WildBerriesScraper:
    def __init__(self):
        self.session = requests.Session()
        self.update_headers()
    
    def update_headers(self):
        """Обновляет заголовки для запросов"""
        self.session.headers.update({
            'User-Agent': get_random_user_agent(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })
    
    def get_product_data(self, product_id):
        """Получает данные о товаре по его ID"""
        url = f"https://card.wb.ru/cards/detail?nm={product_id}"
        
        for attempt in range(MAX_RETRIES):
            try:
                # Обновляем заголовки перед запросом
                self.update_headers()
                
                # Делаем запрос с таймаутом
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Проверяем наличие данных о товаре
                    if 'data' in data and 'products' in data['data'] and len(data['data']['products']) > 0:
                        product = data['data']['products'][0]
                        
                        # Получаем дополнительные данные (цены, наличие)
                        prices_data = self._get_product_prices(product_id)
                        
                        # Форматируем данные в единую структуру
                        result = {
                            'wb_id': str(product_id),
                            'name': product.get('name', ''),
                            'brand': product.get('brand', ''),
                            'category': self._extract_category(product),
                            'seller': {
                                'id': product.get('supplierId', 0),
                                'name': product.get('supplierName', '')
                            },
                            'rating': product.get('rating', 0),
                            'feedbacks_count': product.get('feedbacks', 0),
                            'price': {
                                'current': prices_data.get('current_price'),
                                'original': prices_data.get('original_price'),
                                'discount_percentage': prices_data.get('discount_percentage')
                            },
                            'stocks': self._extract_stocks(product)
                        }
                        
                        return result
                    else:
                        logger.warning(f"Товар {product_id} не найден или данные отсутствуют")
                else:
                    logger.warning(f"Ошибка запроса: {response.status_code}")
                
            except Exception as e:
                logger.error(f"Ошибка при запросе товара {product_id}: {e}")
            
            # Ждем перед повторной попыткой
            delay = get_random_delay(RETRY_DELAY * (2 ** attempt))
            logger.info(f"Повторная попытка через {delay} сек...")
            time.sleep(delay)
        
        return None
    
    def _get_product_prices(self, product_id):
        """Получает данные о ценах товара"""
        url = f"https://wbxcatalog-ru.wildberries.ru/nm-2-card/catalog?spp=0&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,22,66,31,48,1,40,71&stores=117673,122258,122259,125238,125239,125240,507,3158,117501,120602,120762,6158,121709,124731,130744,159402,2737,117986,1733,686,132043&nm={product_id}"
        
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'products' in data['data'] and len(data['data']['products']) > 0:
                    product = data['data']['products'][0]
                    
                    current_price = product.get('salePriceU', 0) / 100 if 'salePriceU' in product else 0
                    original_price = product.get('priceU', 0) / 100 if 'priceU' in product else current_price
                    
                    discount_percentage = 0
                    if original_price > 0 and current_price < original_price:
                        discount_percentage = round((1 - current_price / original_price) * 100, 2)
                    
                    return {
                        'current_price': current_price,
                        'original_price': original_price,
                        'discount_percentage': discount_percentage
                    }
        except Exception as e:
            logger.error(f"Ошибка при получении цен товара {product_id}: {e}")
        
        return {
            'current_price': 0,
            'original_price': 0,
            'discount_percentage': 0
        }
    
    def _extract_category(self, product):
        """Извлекает категорию товара из данных"""
        if 'subj' in product and 'name' in product['subj']:
            return product['subj']['name']
        return "Без категории"
    
    def _extract_stocks(self, product):
        """Извлекает данные о наличии товара на складах"""
        stocks = {}
        
        if 'sizes' in product:
            for size in product['sizes']:
                if 'stocks' in size:
                    for stock in size['stocks']:
                        warehouse_id = stock.get('wh', 0)
                        quantity = stock.get('qty', 0)
                        
                        if warehouse_id in stocks:
                            stocks[warehouse_id] += quantity
                        else:
                            stocks[warehouse_id] = quantity
        
        return stocks
    
    def get_category_products(self, category_id, page=1, limit=100):
        """Получает список товаров из категории"""
        url = f"https://catalog.wb.ru/catalog/{category_id}/catalog"
        params = {
            "appType": 1,
            "couponsGeo": "12,3,18,15,21",
            "curr": "rub",
            "dest": "-1029256,-102269,-1278703,-1255563",
            "emp": 0,
            "lang": "ru",
            "locale": "ru",
            "page": page,
            "pricemarginCoeff": 1.0,
            "reg": 1,
            "regions": "80,64,83,4,38,33,70,82,69,68,86,75,30,40,48,1,22,66,31,71",
            "sort": "popular",
            "spp": 0,
            "limit": limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'products' in data['data']:
                    return data['data']['products']
        except Exception as e:
            logger.error(f"Ошибка при получении товаров категории {category_id}: {e}")
        
        return []
    
    def get_seller_products(self, seller_id, page=1, limit=100):
        """Получает список товаров продавца"""
        url = f"https://catalog.wb.ru/sellers/catalog"
        params = {
            "appType": 1,
            "couponsGeo": "12,3,18,15,21",
            "curr": "rub",
            "dest": "-1029256,-102269,-1278703,-1255563",
            "emp": 0,
            "lang": "ru",
            "locale": "ru",
            "page": page,
            "pricemarginCoeff": 1.0,
            "reg": 1,
            "regions": "80,64,83,4,38,33,70,82,69,68,86,75,30,40,48,1,22,66,31,71",
            "sort": "popular",
            "spp": 0,
            "limit": limit,
            "supplier": seller_id
        }
        
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'products' in data['data']:
                    return data['data']['products']
        except Exception as e:
            logger.error(f"Ошибка при получении товаров продавца {seller_id}: {e}")
        
        return []
    
    def get_product_feedbacks(self, product_id, page=1, limit=10):
        """Получает отзывы на товар"""
        url = f"https://feedbacks2.wb.ru/feedbacks/v1/{product_id}"
        params = {
            "page": page,
            "limit": limit,
            "sort": "date",
            "order": "desc"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if 'feedbacks' in data:
                    return data['feedbacks']
        except Exception as e:
            logger.error(f"Ошибка при получении отзывов товара {product_id}: {e}")
        
        return []
    
    def search_products(self, query, page=1, limit=100):
        """Ищет товары по запросу"""
        url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
        params = {
            "appType": 1,
            "couponsGeo": "12,3,18,15,21",
            "curr": "rub",
            "dest": "-1029256,-102269,-1278703,-1255563",
            "emp": 0,
            "lang": "ru",
            "locale": "ru",
            "page": page,
            "pricemarginCoeff": 1.0,
            "reg": 1,
            "regions": "80,64,83,4,38,33,70,82,69,68,86,75,30,40,48,1,22,66,31,71",
            "sort": "popular",
            "spp": 0,
            "query": query,
            "resultset": "catalog",
            "limit": limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'products' in data['data']:
                    return data['data']['products']
        except Exception as e:
            logger.error(f"Ошибка при поиске товаров по запросу '{query}': {e}")
        
        return []