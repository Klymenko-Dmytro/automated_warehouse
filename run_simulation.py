import os
import sys
import time
import random
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automated_warehouse.settings')
django.setup()

from warehouse.models import Cell, Product, WarehouseLog

# Списки для генерації випадкових товарів
PRODUCT_NAMES = ['Молоко "Ферма" 2.5%', 'Хліб "Тостовий"', 'Сік "Садочок" Яблуко', 'Кава Jacobs Monarch',
                 'Чай Greenfield', 'Шоколад Roshen']


def generate_barcode():
    return "".join([str(random.randint(0, 9)) for _ in range(13)])


def simulate_warehouse():
    print("=== Симуляцію складу ЗАПУЩЕНО. Натисніть Ctrl+C для зупинки ===")

    while True:
        try:
            # Випадково вирішуємо: додати товар (70% шанс) чи видалити (30% шанс)
            action = random.choice(['ADD', 'ADD', 'ADD', 'REMOVE'])

            if action == 'ADD':
                # Шукаємо першу ліпшу вільну комірку
                free_cell = Cell.objects.filter(is_occupied=False).first()

                if free_cell:
                    name = random.choice(PRODUCT_NAMES)
                    barcode = generate_barcode()

                    # Створюємо товар і прив'язуємо до комірки
                    product = Product.objects.create(name=name, barcode=barcode, cell=free_cell)

                    # Позначаємо комірку як зайняту
                    free_cell.is_occupied = True
                    free_cell.save()

                    # Формуємо повідомлення для логу
                    msg = f"Додано на склад: {product.name} ({product.barcode}) за адресою: Зона {free_cell.zone}, Ряд {free_cell.row}, Пол. {free_cell.shelf}, Місце {free_cell.position}"
                    WarehouseLog.objects.create(action_type='ADD', message=msg)
                    print(msg)
                else:
                    print("Склад повний! Немає вільних комірок.")

            elif action == 'REMOVE':
                # Беремо випадковий товар, який зараз є на складі
                product_to_remove = Product.objects.order_by('?').first()

                if product_to_remove:
                    cell = product_to_remove.cell

                    # Звільняємо комірку
                    if cell:
                        cell.is_occupied = False
                        cell.save()

                    msg = f"Вилучено зі складу: {product_to_remove.name} ({product_to_remove.barcode}) з адреси: Зона {cell.zone}, Ряд {cell.row}, Пол. {cell.shelf}, Місце {cell.position}"
                    WarehouseLog.objects.create(action_type='REMOVE', message=msg)
                    print(msg)

                    # Видаляємо товар з бази
                    product_to_remove.delete()
                else:
                    print("Склад пустий, нічого вилучати.")

            # Чекаємо 4 секунди перед наступною дією
            time.sleep(4)

        except KeyboardInterrupt:
            print("\n=== Симуляцію зупинено ===")
            sys.exit()


if __name__ == '__main__':
    simulate_warehouse()
