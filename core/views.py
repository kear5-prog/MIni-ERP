from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Product, Customer, SalesOrder
from .forms import ProductForm, CustomerForm, SalesOrderForm, OrderItemFormSet


def dashboard(request):
    return render(request, "core/dashboard.html", {
        "product_count": Product.objects.count(),
        "customer_count": Customer.objects.count(),
        "order_count": SalesOrder.objects.count(),
    })


# ---------- Products ----------
def product_list(request):
    products = Product.objects.order_by("sku")
    return render(request, "core/product_list.html", {"products": products})


def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product created.")
        return redirect("product_list")
    return render(request, "core/form.html", {"title": "New Product", "form": form})


def product_edit(request, pk):
    obj = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product updated.")
        return redirect("product_list")
    return render(request, "core/form.html", {"title": "Edit Product", "form": form})


# ---------- Customers ----------
def customer_list(request):
    customers = Customer.objects.order_by("name")
    return render(request, "core/customer_list.html", {"customers": customers})


def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Customer created.")
        return redirect("customer_list")
    return render(request, "core/form.html", {"title": "New Customer", "form": form})


def customer_edit(request, pk):
    obj = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Customer updated.")
        return redirect("customer_list")
    return render(request, "core/form.html", {"title": "Edit Customer", "form": form})


# ---------- Sales Orders ----------
def order_list(request):
    orders = SalesOrder.objects.select_related("customer").order_by("-created_at")
    return render(request, "core/order_list.html", {"orders": orders})


def order_create(request):
    order_form = SalesOrderForm(request.POST or None)
    order = SalesOrder()  # unsaved for formset binding

    formset = OrderItemFormSet(request.POST or None, instance=order)

    if request.method == "POST" and order_form.is_valid() and formset.is_valid():
        order = order_form.save()  # now saved
        formset.instance = order
        formset.save()
        messages.success(request, "Sales Order created.")
        return redirect("order_detail", pk=order.pk)

    return render(request, "core/order_form.html", {
        "order_form": order_form,
        "formset": formset,
    })


def order_detail(request, pk):
    order = get_object_or_404(SalesOrder.objects.select_related("customer"), pk=pk)
    items = order.items.select_related("product").all()
    return render(request, "core/order_detail.html", {
        "order": order,
        "items": items,
    })


def order_confirm(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    try:
        order.confirm()
        messages.success(request, "Order confirmed. Stock deducted.")
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("order_detail", pk=pk)
