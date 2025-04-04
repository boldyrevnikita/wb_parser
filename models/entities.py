from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

@dataclass
class Price:
    """Модель данных о цене товара"""
    current: float
    original: Optional[float] = None
    discount_percentage: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Seller:
    """Модель данных о продавце"""
    id: int
    name: str
    rating: Optional[float] = None
    products_count: Optional[int] = None

@dataclass
class Product:
    """Модель данных о товаре"""
    wb_id: str
    name: str
    brand: str
    category: str
    seller: Seller
    rating: Optional[float] = None
    feedbacks_count: Optional[int] = None
    price: Optional[Price] = None
    stocks: Dict[int, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class Feedback:
    """Модель данных об отзыве"""
    product_id: int
    user_id: Optional[str] = None
    rating: int = 0
    text: Optional[str] = None
    likes: int = 0
    dislikes: int = 0
    created_at: Optional[datetime] = None
    parsed_at: datetime = field(default_factory=datetime.now)