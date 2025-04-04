-- Подключение к базе данных
\c wildberries_parser

-- Таблица брендов
CREATE TABLE IF NOT EXISTS brands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица категорий
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица продавцов
CREATE TABLE IF NOT EXISTS sellers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    rating FLOAT,
    products_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица товаров
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    wb_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(512) NOT NULL,
    brand_id INTEGER REFERENCES brands(id),
    category_id INTEGER REFERENCES categories(id),
    seller_id INTEGER REFERENCES sellers(id),
    rating FLOAT,
    feedbacks_count INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица цен на товары
CREATE TABLE IF NOT EXISTS product_prices (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    current_price NUMERIC(15,2) NOT NULL,
    original_price NUMERIC(15,2),
    discount_percentage NUMERIC(5,2),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Таблица наличия товаров
CREATE TABLE IF NOT EXISTS product_stocks (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    warehouse_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Таблица с отзывами
CREATE TABLE IF NOT EXISTS feedbacks (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    user_id VARCHAR(100),
    rating INTEGER NOT NULL,
    text TEXT,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    parsed_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_products_wb_id ON products(wb_id);
CREATE INDEX IF NOT EXISTS idx_product_prices_product_id ON product_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_product_prices_timestamp ON product_prices(timestamp);
CREATE INDEX IF NOT EXISTS idx_product_stocks_product_id ON product_stocks(product_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_product_id ON feedbacks(product_id);