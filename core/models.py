from django.db import models, transaction
from django.core.exceptions import ValidationError



class Product(models.Model):
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    def confirm(self):
        if self.status == self.Status.CONFIRMED:
            return

        items = self.items.select_related("product").all()
        if not items:
            raise ValidationError("Cannot confirm: no order lines.")

        for item in items:
            if item.quantity > item.product.stock_qty:
                raise ValidationError(
                    f"Not enough stock for {item.product.name}"
                )

        with transaction.atomic():
            for item in items:
                product = item.product
                product.stock_qty -= item.quantity
                product.save(update_fields=["stock_qty"])

            self.status = self.Status.CONFIRMED
            self.save(update_fields=["status"])

    def __str__(self):
        return f"SO-{self.id}"
    @property
    def total_amount(self):
        return sum((i.quantity * i.unit_price) for i in self.items.all())



class OrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product} x {self.quantity}"
