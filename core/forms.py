from django import forms
from django.forms import inlineformset_factory
from .models import Product, Customer, SalesOrder, OrderItem, Vendor, PurchaseOrder, PurchaseOrderItem


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "price", "stock_qty"]


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email"]


class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ["customer"]


OrderItemFormSet = inlineformset_factory(
    SalesOrder,
    OrderItem,
    fields=["product", "quantity", "unit_price"],
    extra=1,
    can_delete=True,
)

class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "phone", "address"]


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["vendor"]


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    fields=["product", "quantity", "unit_price"],
    extra=1,
    can_delete=True,
)


class HistoricalDataUploadForm(forms.Form):
    file = forms.FileField(label="Upload CSV File")




