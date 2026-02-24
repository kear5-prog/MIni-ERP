from django.contrib import admin
from .models import Product, Customer, SalesOrder, OrderItem, HistoricalData


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


from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

# Explicit registration (most reliable)
admin.site.register(Product, ProductAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(SalesOrder, SalesOrderAdmin)

class OrderLineResource(resources.ModelResource):
    customer = Field(
        column_name='Customer',
        attribute='customer',
        widget=ForeignKeyWidget(Customer, 'name')
    )
    sku = Field(
        column_name='SKU',
        attribute='sku',
        widget=ForeignKeyWidget(Product, 'sku')  # Validates SKU must exist in Product
    )
    product_name = Field(column_name='Product Name', attribute='product_name')
    uom = Field(column_name='UOM', attribute='uom')
    qty = Field(column_name='QTY', attribute='qty')
    unit_price = Field(column_name='Price', attribute='unit_price')
    month = Field(column_name='Month', attribute='month')
    year = Field(column_name='Year', attribute='year')

    class Meta:
        model = HistoricalData
        # Import uses these fields to prevent duplicate rows over month/year
        import_id_fields = ('sku', 'month', 'year')
        fields = ('customer', 'sku', 'product_name', 'uom', 'qty', 'unit_price', 'month', 'year')

@admin.register(HistoricalData)
class OrderLineAdmin(ImportExportModelAdmin):
    resource_class = OrderLineResource
    list_display = ("sku", "customer", "product_name", "qty", "unit_price", "month", "year")
    list_filter = ("month", "year", "sku")
