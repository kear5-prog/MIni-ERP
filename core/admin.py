from django.contrib import admin
from .models import Product, Customer, SalesOrder, OrderItem


class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "price", "stock_qty")
    search_fields = ("sku", "name")


class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email")
    search_fields = ("name", "phone", "email")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]


# Explicit registration (most reliable)
admin.site.register(Product, ProductAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(SalesOrder, SalesOrderAdmin)
