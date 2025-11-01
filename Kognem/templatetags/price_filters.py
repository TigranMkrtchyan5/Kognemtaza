# Kognem/templatetags/price_filters.py

from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='short_price')
def short_price(value):
    """
    Конвертирует число в формат M[тыс]K[остаток]
    Например: 4864421 -> 4M864K421
    """
    try:
        # 1. Преобразуем значение в целое число (убираем копейки)
        number = int(Decimal(value))
    except:
        return value

    if number < 1000:
        # Если меньше тысячи, возвращаем как есть
        return str(number)

    # 2. Инициализация переменных
    output = []
    
    # 3. Выделяем миллионы (M)
    millions = number // 1000000
    remainder = number % 1000000

    if millions > 0:
        output.append(f"{millions}M")

    # 4. Выделяем тысячи (K)
    # Тысячи всегда должны отображаться тремя цифрами, если они есть
    if remainder > 0:
        thousands = remainder // 1000
        remainder = remainder % 1000

        # Форматируем тысячи тремя цифрами, если в разряде миллионов что-то было
        if millions > 0:
            # Если были миллионы, форматируем тысячи как 000, 001, 864
            thousands_str = f"{thousands:03}"
            output.append(f"{thousands_str}K")
        elif thousands > 0:
            # Если нет миллионов, но есть тысячи (10K), форматируем просто как 10K
            output.append(f"{thousands}K")

    # 5. Выделяем остаток (сотни)
    # Остаток всегда должен отображаться тремя цифрами, если в нем есть что-то
    if remainder > 0 or (number % 1000 == 0 and number >= 1000000):
        # Если остаток меньше 1000, форматируем его тремя цифрами
        remainder_str = f"{remainder:03}"
        # Добавляем остаток, только если были миллионы или тысячи
        if millions > 0 or (number >= 1000 and number < 1000000):
             output.append(remainder_str)

    # 6. Собираем строку
    return "".join(output).replace("K000", "K") # Убираем K000, если остаток 0