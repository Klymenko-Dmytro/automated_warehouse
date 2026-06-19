from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q, Sum
from .models import Cell, Product, WarehouseLog
import json
from django.views.decorators.csrf import csrf_exempt


def index(name_request):
    """Головна сторінка складу з групуванням для 2D-карти"""
    query = name_request.GET.get('q', '').strip()
    highlighted_cell_id = None
    search_error = None

    if query:
        # Шукаємо товар за назвою або штрихкодом
        product = Product.objects.filter(
            Q(name__icontains=query) | Q(barcode=query)
        ).first()
        if product and product.cell:
            highlighted_cell_id = product.cell.id
        else:
            search_error = "Товар не знайдено або він не розміщений у комірці."

    # Отримуємо всі комірки
    cells = Cell.objects.all().order_by('zone', 'row', 'shelf', 'position')

    # Групуємо комірки у структуру: Зона -> Ряд -> Полиця -> Список місць
    warehouse_structure = {}
    for cell in cells:
        if cell.zone not in warehouse_structure:
            warehouse_structure[cell.zone] = {}
        if cell.row not in warehouse_structure[cell.zone]:
            warehouse_structure[cell.zone][cell.row] = {}
        if cell.shelf not in warehouse_structure[cell.zone][cell.row]:
            warehouse_structure[cell.zone][cell.row][cell.shelf] = []
        warehouse_structure[cell.zone][cell.row][cell.shelf].append(cell)

    logs = WarehouseLog.objects.all()[:15]

    context = {
        'warehouse_structure': warehouse_structure,
        'logs': logs,
        'query': query,
        'highlighted_cell_id': highlighted_cell_id,
        'search_error': search_error
    }
    return render(name_request, 'warehouse/index.html', context)


def api_warehouse_data(request):
    """Ендпоінт для JavaScript: повертає актуальний стан складу з урахуванням кількості товарів"""
    cells = Cell.objects.all().values('id', 'zone', 'row', 'shelf', 'position', 'is_occupied')

    # Агрегуємо товари в комірках, щоб коректно віддати інформацію на фронтенд
    products = Product.objects.all().select_related('cell')

    # Оскільки в комірці може бути товар, згрупуємо дані
    product_map = {}
    for p in products:
        if p.cell_id:
            if p.cell_id not in product_map:
                product_map[p.cell_id] = {
                    "name": p.name,
                    "barcode": p.barcode,
                    "quantity": 0
                }
            # Сумуємо кількість, якщо в комірці раптом опинилося кілька записів цього товару
            product_map[p.cell_id]["quantity"] += p.quantity

    cells_list = []
    for c in cells:
        c_id = c['id']
        # Передаємо інформацію про товар разом із його кількістю
        c['product'] = product_map.get(c_id, None)
        cells_list.append(c)

    logs = WarehouseLog.objects.all()[:15]
    logs_list = [f"[{log.created_at.strftime('%H:%M:%S')}] {log.message}" for log in logs]

    return JsonResponse({
        'cells': cells_list,
        'logs': logs_list
    })


@csrf_exempt
def api_manual_add(request):
    """Ручне додавання товару з контролем змішування (макс. 100 одиниць на комірку)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cell_id = data.get('cell_id')
            name = data.get('name', '').strip()
            barcode = data.get('barcode', '').strip()

            # Перевіряємо та перетворюємо введену кількість у число
            try:
                quantity = int(data.get('quantity', 1))
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Некоректна кількість товару!'}, status=400)

            if not name or not barcode:
                return JsonResponse({'status': 'error', 'message': 'Заповніть всі поля!'}, status=400)
            if quantity <= 0:
                return JsonResponse({'status': 'error', 'message': 'Кількість має бути більшою за 0!'}, status=400)

            початкова_комірка = Cell.objects.get(id=cell_id)

            # Контроль змішування: якщо в обраній комірці вже лежить ІНШИЙ товар, ручне додавання блокується
            існуючий_товар_в_комірці = початкова_комірка.products.first()
            if існуючий_товар_в_комірці and існуючий_товар_в_комірці.barcode != barcode:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Помилка: Комірка зайнята іншим товаром ({існуючий_товар_в_комірці.name})! Виберіть порожню комірку.'
                }, status=400)

            залишок_для_розміщення = quantity
            MAKS_MISKIST = 100

            # Алгоритм: беремо початкову комірку, а для залишку партії використовуємо ВСІ АБСОЛЮТНО ПОРОЖНІ комірки складу
            порожні_комірки = Cell.objects.filter(products__isnull=True).exclude(id=початкова_комірка.id).order_by(
                'zone', 'row', 'shelf', 'position')
            доступні_комірки = [початкова_комірка] + list(порожні_комірки)

            інформація_про_розміщення = []

            for комірка in доступні_комірки:
                if залишок_для_розміщення <= 0:
                    break

                # Додаткова захисна перевірка всередині циклу
                поточний_товар = комірка.products.first()
                if поточний_товар and поточний_товар.barcode != barcode:
                    continue

                поточна_кількість = sum(p.quantity for p in комірка.products.all())
                вільне_місце = MAKS_MISKIST - поточна_кількість

                if вільне_місце > 0:
                    кількість_до_запису = min(залишок_для_розміщення, вільне_місце)

                    if поточний_товар:
                        поточний_товар.quantity += кількість_до_запису
                        поточний_товар.save()
                    else:
                        Product.objects.create(name=name, barcode=barcode, cell=комірка, quantity=кількість_до_запису)

                    залишок_для_розміщення -= кількість_до_запису
                    інформація_про_розміщення.append(
                        f"{кількість_до_запису} шт. у [{комірка.zone}-Р{комірка.row}-П{комірка.shelf}-М{комірка.position}]")

                    if (поточна_кількість + кількість_до_запису) >= MAKS_MISKIST:
                        комірка.is_occupied = True
                        комірка.save()

            if залишок_для_розміщення > 0:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Не вистачило вільних комірок! Не вдалося розмістити ще {залишок_для_розміщення} шт.'
                }, status=400)

            msg = f"[РУЧНЕ] Додано товар: {name} ({barcode}), всього {quantity} шт. Розподілено: {', '.join(інформація_про_розміщення)}"
            WarehouseLog.objects.create(action_type='ADD', message=msg)

            return JsonResponse({'status': 'success', 'message': f'Товар успішно додано ({quantity} шт.)!'})

        except Cell.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Комірку не знайдено.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Некоректний метод.'}, status=405)


@csrf_exempt
def api_manual_remove(request):
    """Ручне вилучення певної кількості товару з комірки"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cell_id = data.get('cell_id')

            try:
                quantity_to_remove = int(data.get('quantity', 1))
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Некоректна кількість для вилучення!'}, status=400)

            cell = Cell.objects.get(id=cell_id)
            products = cell.products.all()

            total_in_cell = sum(p.quantity for p in products)

            if total_in_cell == 0:
                return JsonResponse({'status': 'error', 'message': 'В цій комірці немає товару.'}, status=400)

            if quantity_to_remove > total_in_cell:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Не можна вилучити {quantity_to_remove} шт. В комірці є тільки {total_in_cell} шт.'
                }, status=400)

            qty_left_to_remove = quantity_to_remove
            product_name = ""
            product_barcode = ""

            for product in products:
                if qty_left_to_remove <= 0:
                    break

                product_name = product.name
                product_barcode = product.barcode

                if product.quantity <= qty_left_to_remove:
                    qty_left_to_remove -= product.quantity
                    product.delete()
                else:
                    product.quantity -= qty_left_to_remove
                    product.save()
                    qty_left_to_remove = 0

            # Оскільки товар вилучили, комірка точно тепер не зайнята повністю
            cell.is_occupied = False
            cell.save()

            msg = f"[РУЧНЕ] Вилучено {quantity_to_remove} шт.: {product_name} ({product_barcode}) з {cell.zone}-Р{cell.row}-П{cell.shelf}-М{cell.position}"
            WarehouseLog.objects.create(action_type='REMOVE', message=msg)

            return JsonResponse({'status': 'success', 'message': f'Вилучено {quantity_to_remove} шт. товару!'})

        except Cell.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Комірку не знайдено.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Некоректний метод.'}, status=405)
