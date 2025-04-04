import random
import time

def get_random_user_agent(user_agents):
    """Возвращает случайный User-Agent из списка"""
    return random.choice(user_agents)

def get_random_delay(base_delay):
    """Возвращает случайную задержку на основе базовой"""
    # Добавляем +/- 30% к базовой задержке
    return base_delay * (1 + random.uniform(-0.3, 0.3))

def exponential_backoff(attempt, base_delay=1, max_delay=60):
    """Рассчитывает задержку для повторных попыток с экспоненциальной задержкой"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay * (1 + random.uniform(-0.1, 0.1))  # Добавляем случайность