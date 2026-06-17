from django.db import models

class Cell(models.Model):
    """Модель складської комірки (адресне зберігання)"""
    zone = models.CharField(max_length=10, verbose_name="Відділ/Зона")  # наприклад, 'A'
    row = models.IntegerField(verbose_name="Ряд")                    # наприклад, 2
    shelf = models.IntegerField(verbose_name="Полиця")                # наприклад, 1
    position = models.IntegerField(verbose_name="Місце")              # наприклад, 4
    is_occupied = models.BooleanField(default=False, verbose_name="Зайнята")

    class Meta:
        # Унікальне поєднання координат, щоб не було дублів комірок
        unique_together = ('zone', 'row', 'shelf', 'position')
        verbose_name = "Комірка"
        verbose_name_plural = "Комірки"

    def __str__(self):
        return f"Зона {self.zone} | Ряд {self.row} | Пол. {self.shelf} | Місце {self.position}"


class Product(models.Model):
    """Модель товару"""
    name = models.CharField(max_length=255, verbose_name="Назва товару")
    barcode = models.CharField(max_length=50, unique=True, verbose_name="Штрихкод")
    # Зв'язок один-до-одного (або багатьом до одного, якщо в комірці кілька товарів).
    # Поки робимо: одна комірка — один товар.
    cell = models.OneToOneField(
        Cell,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product",
        verbose_name="Комірка зберігання"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата додавання")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товари"

    def __str__(self):
        return f"{self.name} ({self.barcode})"


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
        ordering = ['-created_at']  # Свіжі логи будуть зверху

    def __str__(self):
        return f"[{self.created_at.strftime('%H:%M:%S')}] {self.message}"
