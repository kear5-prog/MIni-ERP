from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
import csv
from datetime import datetime
from core.services import forecasting

from .models import (
    Product, Customer, SalesOrder,
    Vendor, PurchaseOrder, HistoricalData
)
from .forms import (
    ProductForm, CustomerForm, SalesOrderForm, OrderItemFormSet,
    VendorForm, PurchaseOrderForm, PurchaseOrderItemFormSet, HistoricalDataUploadForm
)

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


# ---------- Vendors ----------
def vendor_list(request):
    vendors = Vendor.objects.order_by("name")
    return render(request, "core/vendor_list.html", {"vendors": vendors})

def vendor_create(request):
    form = VendorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vendor created.")
        return redirect("vendor_list")
    return render(request, "core/form.html", {"title": "New Vendor", "form": form})

def vendor_edit(request, pk):
    obj = get_object_or_404(Vendor, pk=pk)
    form = VendorForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vendor updated.")
        return redirect("vendor_list")
    return render(request, "core/form.html", {"title": "Edit Vendor", "form": form})


# ---------- Purchase Orders ----------
def purchase_order_list(request):
    orders = PurchaseOrder.objects.select_related("vendor").order_by("-created_at")
    return render(request, "core/purchase_order_list.html", {"orders": orders})

def purchase_order_create(request):
    order_form = PurchaseOrderForm(request.POST or None)
    order = PurchaseOrder()

    formset = PurchaseOrderItemFormSet(request.POST or None, instance=order)

    if request.method == "POST" and order_form.is_valid() and formset.is_valid():
        order = order_form.save()
        formset.instance = order
        formset.save()
        messages.success(request, "Purchase Order created.")
        return redirect("purchase_order_detail", pk=order.pk)

    return render(request, "core/order_form.html", {
        "order_form": order_form,
        "formset": formset,
        "title": "New Purchase Order"
    })

def purchase_order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder.objects.select_related("vendor"), pk=pk)
    items = order.items.select_related("product").all()
    return render(request, "core/purchase_order_detail.html", {
        "order": order,
        "items": items,
    })

def purchase_order_confirm(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        order.confirm()
        messages.success(request, "Purchase Order confirmed. Stock added.")
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("purchase_order_detail", pk=pk)


# ---------- Historical Data Upload ----------
def upload_historical_data(request):
    form = HistoricalDataUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        csv_file = form.cleaned_data["file"]
        if not csv_file.name.endswith(".csv"):
            messages.error(request, "Please upload a CSV file.")
            return redirect("upload_history")

        try:
            # We assume CSV comes with headers: SKU code, Product Description, UOM, Consummption, Unit Price, Month, Year
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            records_created = 0
            for row in reader:
                HistoricalData.objects.create(
                    sku=row.get("SKU code", ""),
                    product_name=row.get("Product Description", ""),
                    uom=row.get("UOM", "PCS"),
                    consumption=int(row.get("Consummption", 0)),
                    unit_price=float(row.get("Unit Price", 0.0)),
                    month=int(row.get("Month", 1)),
                    year=int(row.get("Year", datetime.now().year))
                )
                records_created += 1
                
            messages.success(request, f"Successfully uploaded {records_created} historical records.")
            return redirect("dashboard")
            
        except Exception as e:
            messages.error(request, f"Error parsing CSV file: {str(e)}")

    return render(request, "core/form.html", {
        "title": "Upload Historical Data",
        "form": form
    })

# ---------- Forecasting ----------
def forecast_dashboard(request):
    products = Product.objects.all()
    context = {"products": products, "selected_sku_list": [], "selected_mode_list": []}
    
    if request.method == "POST":
        sku_id = request.POST.get("sku")
        mode = request.POST.get("mode") # single or compare
        context["selected_sku_list"] = [int(sku_id)] if sku_id else []
        context["selected_mode_list"] = [mode] if mode else []
        horizon = int(request.POST.get("horizon", 6))
        sma_window = int(request.POST.get("sma_window", 3))
        # Handle empty alpha if using estimation
        alpha_raw = request.POST.get("ses_alpha")
        ses_alpha = float(alpha_raw) if alpha_raw else None
        hw_season = int(request.POST.get("hw_season", 12))
        
        selected_product = get_object_or_404(Product, pk=sku_id)
        context["selected_product"] = selected_product
        
        ts = forecasting.get_sku_timeseries(selected_product)
        if ts is None or len(ts) < sma_window:
            context["error"] = f"Not enough historical data for {selected_product.name}. Require at least {sma_window} months."
            return render(request, "core/forecast.html", context)
            
        forecasts_dict = {}
        metrics = [] # list of dicts: {'method': '', 'mape': 0, 'rmse': 0}
        
        try:
            if mode in ["SMA", "Compare"]:
                fitted_sma, fc_sma = forecasting.run_sma(ts, sma_window, horizon)
                forecasts_dict["SMA"] = fc_sma
                mape_sma, rmse_sma = forecasting.evaluate_metrics(ts, fitted_sma)
                metrics.append({"method": "SMA", "mape": mape_sma, "rmse": rmse_sma})
                
            if mode in ["SES", "Compare"]:
                fitted_ses, fc_ses = forecasting.run_ses(ts, ses_alpha, horizon)
                forecasts_dict["SES"] = fc_ses
                mape_ses, rmse_ses = forecasting.evaluate_metrics(ts, fitted_ses)
                metrics.append({"method": "SES", "mape": mape_ses, "rmse": rmse_ses})
                
            if mode in ["HW", "Compare"]:
                # HW needs at least 2*season periods
                if len(ts) >= hw_season * 2:
                    fitted_hw, fc_hw = forecasting.run_holt_winters(ts, hw_season, horizon)
                    forecasts_dict["Holt-Winters"] = fc_hw
                    mape_hw, rmse_hw = forecasting.evaluate_metrics(ts, fitted_hw)
                    metrics.append({"method": "Holt-Winters", "mape": mape_hw, "rmse": rmse_hw})
                elif mode == "HW":
                     context["error"] = f"Holt-Winters requires {hw_season*2} periods. Only {len(ts)} available."
                     return render(request, "core/forecast.html", context)
                     
            if not forecasts_dict:
                context["error"] = "No forecasting methods could run with current parameters."
                return render(request, "core/forecast.html", context)

            # Rank metrics by MAPE
            metrics.sort(key=lambda x: x['mape'] if x['mape'] is not None else float('inf'))
            for i, m in enumerate(metrics):
                m['rank'] = i + 1
            
            context["metrics"] = metrics
            if len(metrics) > 1:
                 context["best_method"] = metrics[0]
                 
            chart_html = forecasting.generate_forecast_chart(
                ts, 
                forecasts_dict, 
                f"Demand Forecast: {selected_product.name}"
            )
            context["chart_html"] = chart_html
            
        except Exception as e:
            context["error"] = f"Forecasting Error: {str(e)}"
            
    return render(request, "core/forecast.html", context)


