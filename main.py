import sys
import time
import json
import argparse
from loguru import logger
from pathlib import Path
from datetime import datetime

from parser.scraper import WildBerriesScraper
from database.repository import WildberriesRepository
from parser.helpers import save_to_json

# Настройка логирования
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/parser_{time}.log", rotation="10 MB", retention="1 week", level="DEBUG")

def parse_product(product_id, save_to_db=True, save_json=False):
    """Парсит данные о товаре"""
    scraper = WildBerriesScraper()
    repo = WildberriesRepository() if save_to_db else None
    
    logger.info(f"Начинаем парсинг товара: {product_id}")
    
    product_data = scraper.get_product_data(product_id)
    
    if not product_data:
        logger.error(f"Не удалось получить данные о товаре {product_id}")
        return None
    
    logger.info(f"Данные о товаре {product_id} успешно получены")
    
    # Сохраняем в базу данных
    if save_to_db:
        db_id = repo.save_product(product_data)
        logger.info(f"Товар {product_id} сохранен в БД с ID: {db_id}")
    
    # Сохраняем в JSON
    if save_json:
        json_path = Path(f"data/products/{product_id}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_to_json(product_data, str(json_path))
        logger.info(f"Товар {product_id} сохранен в JSON: {json_path}")
    
    return product_data

def parse_category(category_id, max_pages=1, save_to_db=True, save_json=False):
    """Парсит товары из категории"""
    scraper = WildBerriesScraper()
    
    logger.info(f"Начинаем парсинг категории: {category_id}")
    
    all_products = []
    
    for page in range(1, max_pages + 1):
        logger.info(f"Парсинг страницы {page} категории {category_id}")
        
        products = scraper.get_category_products(category_id, page=page)
        
        if not products:
            logger.warning(f"Нет товаров на странице {page} категории {category_id}")
            break
        
        logger.info(f"Найдено {len(products)} товаров на странице {page}")
        all_products.extend(products)
        
        # Задержка между запросами страниц
        time.sleep(2)
    
    logger.info(f"Всего найдено {len(all_products)} товаров в категории {category_id}")
    
    # Если нужно сохранить в JSON
    if save_json:
        json_path = Path(f"data/categories/{category_id}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_to_json(all_products, str(json_path))
        logger.info(f"Товары категории {category_id} сохранены в JSON: {json_path}")
    
    # Если нужно сохранить в БД, парсим каждый товар отдельно для получения полных данных
    if save_to_db:
        logger.info(f"Начинаем сохранение товаров категории {category_id} в БД")
        
        for product in all_products:
            product_id = product.get('id', product.get('nmId'))
            if product_id:
                parse_product(product_id, save_to_db=True, save_json=False)
                # Задержка между запросами
                time.sleep(2)
    
    return all_products

def parse_seller(seller_id, max_pages=1, save_to_db=True, save_json=False):
    """Парсит товары продавца"""
    scraper = WildBerriesScraper()
    
    logger.info(f"Начинаем парсинг продавца: {seller_id}")
    
    all_products = []
    
    for page in range(1, max_pages + 1):
        logger.info(f"Парсинг страницы {page} продавца {seller_id}")
        
        products = scraper.get_seller_products(seller_id, page=page)
        
        if not products:
            logger.warning(f"Нет товаров на странице {page} продавца {seller_id}")
            break
        
        logger.info(f"Найдено {len(products)} товаров на странице {page}")
        all_products.extend(products)
        
        # Задержка между запросами страниц
        time.sleep(2)
    
    logger.info(f"Всего найдено {len(all_products)} товаров у продавца {seller_id}")
    
    # Если нужно сохранить в JSON
    if save_json:
        json_path = Path(f"data/sellers/{seller_id}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_to_json(all_products, str(json_path))
        logger.info(f"Товары продавца {seller_id} сохранены в JSON: {json_path}")
    
    # Если нужно сохранить в БД, парсим каждый товар отдельно для получения полных данных
    if save_to_db:
        logger.info(f"Начинаем сохранение товаров продавца {seller_id} в БД")
        
        for product in all_products:
            product_id = product.get('id', product.get('nmId'))
            if product_id:
                parse_product(product_id, save_to_db=True, save_json=False)
                # Задержка между запросами
                time.sleep(2)
    
    return all_products

def search_and_parse(query, max_pages=1, save_to_db=True, save_json=False):
    """Ищет и парсит товары по запросу"""
    scraper = WildBerriesScraper()
    
    logger.info(f"Начинаем поиск товаров по запросу: {query}")
    
    all_products = []
    
    for page in range(1, max_pages + 1):
        logger.info(f"Парсинг страницы {page} поискового запроса '{query}'")
        
        products = scraper.search_products(query, page=page)
        
        if not products:
            logger.warning(f"Нет товаров на странице {page} поискового запроса '{query}'")
            break
        
        logger.info(f"Найдено {len(products)} товаров на странице {page}")
        all_products.extend(products)
        
        # Задержка между запросами страниц
        time.sleep(2)
    
    logger.info(f"Всего найдено {len(all_products)} товаров по запросу '{query}'")
    
    # Если нужно сохранить в JSON
    if save_json:
        safe_query = "".join(c for c in query if c.isalnum() or c in [' ', '_']).strip().replace(' ', '_')
        json_path = Path(f"data/search/{safe_query}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_to_json(all_products, str(json_path))
        logger.info(f"Товары по запросу '{query}' сохранены в JSON: {json_path}")
    
    # Если нужно сохранить в БД, парсим каждый товар отдельно для получения полных данных
    if save_to_db:
        logger.info(f"Начинаем сохранение товаров по запросу '{query}' в БД")
        
        for product in all_products:
            product_id = product.get('id', product.get('nmId'))
            if product_id:
                parse_product(product_id, save_to_db=True, save_json=False)
                # Задержка между запросами
                time.sleep(2)
    
    return all_products

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Парсер WildBerries')
    parser.add_argument('--mode', type=str, choices=['product', 'category', 'seller', 'search'], required=True,
                        help='Режим работы парсера')
    parser.add_argument('--id', type=str, help='ID товара, категории или продавца')
    parser.add_argument('--query', type=str, help='Поисковый запрос')
    parser.add_argument('--pages', type=int, default=1, help='Количество страниц для парсинга (по умолчанию 1)')
    parser.add_argument('--no-db', action='store_true', help='Не сохранять в базу данных')
    parser.add_argument('--json', action='store_true', help='Сохранять результаты в JSON')
    
    args = parser.parse_args()
    
    # Создаем папку для логов
    Path("logs").mkdir(exist_ok=True)
    
    # Режим работы
    if args.mode == 'product':
        if not args.id:
            logger.error("Необходимо указать ID товара для режима 'product'")
            return
        
        parse_product(args.id, save_to_db=not args.no_db, save_json=args.json)
        
    elif args.mode == 'category':
        if not args.id:
            logger.error("Необходимо указать ID категории для режима 'category'")
            return
        
        parse_category(args.id, max_pages=args.pages, save_to_db=not args.no_db, save_json=args.json)
        
    elif args.mode == 'seller':
        if not args.id:
            logger.error("Необходимо указать ID продавца для режима 'seller'")
            return
        
        parse_seller(args.id, max_pages=args.pages, save_to_db=not args.no_db, save_json=args.json)
        
    elif args.mode == 'search':
        if not args.query:
            logger.error("Необходимо указать поисковый запрос для режима 'search'")
            return
        
        search_and_parse(args.query, max_pages=args.pages, save_to_db=not args.no_db, save_json=args.json)

if __name__ == "__main__":
    main()