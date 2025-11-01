# price_filters.py

from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='short_price')
def short_price(value):
    """
    Конвертирует большое число в короткий формат (K, M, B).
    Например: 1000000 -> 1M, 15000 -> 15K
    """
    try:
        # Убеждаемся, что работаем с числом (Decimal или float)
        value = Decimal(value)
    except:
        return value

    # Форматирование
    if value >= 1000000000:
        # Миллиарды (B - Billion)
        return f"{value / 1000000000:.1f}B"
    elif value >= 1000000:
        # Миллионы (M - Million)
        # Форматируем до 1 знака после запятой, если это не целое число, 
        # иначе без знака (.1f или .0f)
        formatted_value = value / 1000000
        if formatted_value.as_tuple().exponent >= 0:
            # Целый миллион (1.0M)
            return f"{formatted_value:.0f}M"
        else:
            # Дробный миллион (1.5M)
            return f"{formatted_value:.1f}M"
            
    elif value >= 1000:
        # Тысячи (K - Kilo)
        formatted_value = value / 1000
        if formatted_value.as_tuple().exponent >= 0:
            # Целая тысяча (10K)
            return f"{formatted_value:.0f}K"
        else:
            # Дробная тысяча (1.5K)
            return f"{formatted_value:.1f}K"
    else:
        # Меньше тысячи - просто округляем до целого
        return f"{value:.0f}"