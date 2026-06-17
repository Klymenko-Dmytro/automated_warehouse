import os
import django

# Налаштування оточення Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automated_warehouse.settings')
django.setup()

from warehouse.models import Cell


def create_warehouse_structure():
    # Видаляємо старі комірки, якщо вони були, для чистого старту
    Cell.objects.all().delete()
    print("Очищення старої структури складу...")

    zones = ['A', 'B', 'C']
    rows = range(1, 4)  # 1, 2, 3 ряди
    shelves = range(1, 11)  # 10 полиць
    positions = range(1, 11)  # 10 місць

    cells_to_create = []
    for zone in zones:
        for row in rows:
            for shelf in shelves:
                for pos in positions:
                    cells_to_create.append(
                        Cell(zone=zone, row=row, shelf=shelf, position=pos)
                    )

    Cell.objects.bulk_create(cells_to_create)
    print(f"Успішно створено {len(cells_to_create)} комірок для адресного зберігання!")


if __name__ == '__main__':
    create_warehouse_structure()
