from django.db import models
from django.core.exceptions import ValidationError


class Cell(models.Model):
    """Модель складської комірки (адресне зберігання)"""
    zone = models.CharField(max_length=10, verbose_name="Відділ/Зона")
    row = models.IntegerField(verbose_name="Ряд")
    shelf = models.IntegerField(verbose_name="Полиця")
    position = models.IntegerField(verbose_name="Місце")
    # Тепер означає, що в комірці рівно 100 одиниць товару
    is_occupied = models.BooleanField(default=False, verbose_name="Зайнята повністю")

    class Meta:
        unique_together = ('zone', 'row', 'shelf', 'position')
        verbose_name = "Комірка"
        verbose_name_plural = "Комірки"
        ordering = ['zone', 'row', 'shelf', 'position']

    def __str__(self):
        return f"Зона {self.zone} | Ряд {self.row} | Пол. {self.shelf} | Місце {self.position}"


class Product(models.Model):
    """Модель товару з обліком кількості"""
    MAX_CELL_CAPACITY = 100

    name = models.CharField(max_length=255, verbose_name="Назва товару")
    # Прибрали unique=True, бо однакові товари (один штрихкод) розкидаються по різних комірках
    barcode = models.CharField(max_length=50, verbose_name="Штрихкод")

    # Зв'язок ForeignKey: в одній комірці може бути товар, і один штрихкод може бути в багатьох комірках
    cell = models.ForeignKey(
        Cell,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Комірка зберігання"
    )
    # Нове поле для обліку залишків у комірці
    quantity = models.IntegerField(default=1, verbose_name="Кількість товару")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата додавання")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товари"

    def __str__(self):
        return f"{self.name} ({self.barcode}) — {self.quantity} шт."

    def clean(self):
        """Валідація кількості для ручного введення в панелі керування або адмінці"""
        if self.quantity <= 0:
            raise ValidationError("Кількість товару повинна бути більшою за 0.")
        if self.quantity > self.MAX_CELL_CAPACITY:
            raise ValidationError(f"В одну комірку не можна покласти більше {self.MAX_CELL_CAPACITY} шт. товару.")


class WarehouseLog(models.Model):
    """Модель для збереження логів дій на складі"""
    ACTION_CHOICES = [
        ('ADD', 'Додано'),
        ('REMOVE', 'Вилучено'),
    ]
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Тип дії")
    message = models.TextField(verbose_name="Повідомлення")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час події")

    class Meta:
        verbose_name = "Лог складу"
        verbose_name_plural = "Логи складу"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%H:%M:%S')}] {self.message}"
