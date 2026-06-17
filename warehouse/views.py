from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Cell, Product, WarehouseLog
import json
from django.views.decorators.csrf import csrf_exempt

def index(name_request):
    """Головна сторінка складу з групуванням для 2D-карти"""
    query = name_request.GET.get('q', '').strip()
    highlighted_cell_id = None
    search_error = None

    if query:
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
    # Це дозволить нам зробити красиві відступи між об'єктами в HTML
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
    """Ендпоінт для JavaScript: повертає актуальний стан складу та останні логи"""
    cells = Cell.objects.all().values('id', 'zone', 'row', 'shelf', 'position', 'is_occupied')

    # Формуємо список товарів для передачі назв у комірки
    products = Product.objects.all().select_related('cell')
    product_map = {p.cell.id: {"name": p.name, "barcode": p.barcode} for p in products if p.cell}

    cells_list = []
    for c in cells:
        c_id = c['id']
        c['product'] = product_map.get(c_id, None)
        cells_list.append(c)

    logs = WarehouseLog.objects.all()[:15]
    logs_list = [f"[{log.created_at.strftime('%H:%M:%S')}] {log.message}" for log in logs]

    return JsonResponse({
        'cells': cells_list,
        'logs': logs_list
    })


@csrf_exempt  # Для спрощення презентаційного проекту відключаємо CSRF на цьому ендпоінті
def api_manual_add(request):
    """Ручне додавання товару в комірку"""
    if request.method == 'POST':
        data = json.loads(request.body)
        cell_id = data.get('cell_id')
        name = data.get('name', '').strip()
        barcode = data.get('barcode', '').strip()

        if not name or not barcode:
            return JsonResponse({'status': 'error', 'message': 'Заповніть всі поля!'}, status=400)

        try:
            cell = Cell.objects.get(id=cell_id)
            if cell.is_occupied:
                return JsonResponse({'status': 'error', 'message': 'Комірка вже зайнята!'}, status=400)

            # Перевірка унікальності штрихкоду
            if Product.objects.filter(barcode=barcode).exists():
                return JsonResponse({'status': 'error', 'message': 'Товар з таким штрихкодом вже є на складі!'},
                                    status=400)

            # Створюємо товар та займаємо комірку
            product = Product.objects.create(name=name, barcode=barcode, cell=cell)
            cell.is_occupied = True
            cell.save()

            # Логування
            msg = f"[РУЧНЕ] Додано: {product.name} ({product.barcode}) -> {cell.zone}-Р{cell.row}-П{cell.shelf}-М{cell.position}"
            WarehouseLog.objects.create(action_type='ADD', message=msg)

            return JsonResponse({'status': 'success', 'message': 'Товар успішно додано!'})
        except Cell.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Комірку не знайдено.'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Некоректний метод.'}, status=405)


@csrf_exempt
def api_manual_remove(request):
    """Ручне вилучення товару з комірки"""
    if request.method == 'POST':
        data = json.loads(request.body)
        cell_id = data.get('cell_id')

        try:
            cell = Cell.objects.get(id=cell_id)
            product = Product.objects.filter(cell=cell).first()

            if not product:
                return JsonResponse({'status': 'error', 'message': 'В цій комірці немає товару.'}, status=400)

            msg = f"[РУЧНЕ] Вилучено: {product.name} ({product.barcode}) з {cell.zone}-Р{cell.row}-П{cell.shelf}-М{cell.position}"
            WarehouseLog.objects.create(action_type='REMOVE', message=msg)

            # Видаляємо товар та звільняємо комірку
            product.delete()
            cell.is_occupied = False
            cell.save()

            return JsonResponse({'status': 'success', 'message': 'Товар вилучено!'})
        except Cell.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Комірку не знайдено.'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Некоректний метод.'}, status=405)