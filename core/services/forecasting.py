import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
import plotly.graph_objs as go
import plotly.io as pio

from core.models import HistoricalData, Product

def get_sku_timeseries(product):
    """
    Fetches historical Order Line data for a specific SKU and aggregates it into a monthly time series.
    Returns a Pandas Series indexed by Date.
    """
    records = HistoricalData.objects.filter(sku=product).order_by('year', 'month')
    if not records.exists():
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(list(records.values('qty', 'month', 'year')))
    
    # Create a datetime index representing the start of each month
    df['date'] = pd.to_datetime(df.assign(day=1)[['year', 'month', 'day']])
    
    # Aggregate quantities by date (in case of multiple orders in the same month)
    ts = df.groupby('date')['qty'].sum().astype(float)
    
    # Ensure continuous monthly frequency filling missing months with 0
    if not ts.empty:
        # Generate full date range
        idx = pd.date_range(start=ts.index.min(), end=ts.index.max(), freq='MS')
        ts = ts.reindex(idx, fill_value=0.0)
        
    return ts

def evaluate_metrics(actual, forecast):
    """
    Calculates RMSE and MAPE given true values and predictions.
    """
    # Align indices just in case
    df = pd.DataFrame({'actual': actual, 'forecast': forecast}).dropna()
    if df.empty:
        return None, None
    
    rmse = np.sqrt(mean_squared_error(df['actual'], df['forecast']))
    # Handle division by zero in MAPE by replacing 0 actuals with a very small number, or filter them out
    actual_no_zero = df['actual'].replace(0, 1e-5)
    mape = mean_absolute_percentage_error(actual_no_zero, df['forecast']) * 100
    
    return round(mape, 2), round(rmse, 2)

def run_sma(ts, window_size, forecast_horizon):
    """
    Runs Simple Moving Average forecasting.
    Using the last 'window_size' observations to form the average forecast.
    """
    if len(ts) < window_size:
        raise ValueError(f"Time series length ({len(ts)}) is less than SMA window size ({window_size}).")
        
    # Fit: moving average on historical data
    fitted = ts.rolling(window=window_size).mean()
    
    # Forecast: The last computed MA is flat-lined for the true horizon
    last_ma = fitted.iloc[-1]
    if pd.isna(last_ma):
        last_ma = ts.mean() # Fallback
        
    future_dates = pd.date_range(start=ts.index.max() + pd.DateOffset(months=1), periods=forecast_horizon, freq='MS')
    forecast = pd.Series([last_ma] * forecast_horizon, index=future_dates)
    
    return fitted, forecast

def run_ses(ts, alpha, forecast_horizon):
    """
    Runs Simple Exponential Smoothing.
    """
    if len(ts) < 2:
        raise ValueError("Not enough data for Exponential Smoothing.")
        
    # For SES, statsmodels expects no trend/seasonal
    # We can pass smoothing_level directly or let statsmodels optimize if alpha is None
    kwargs = {'initialization_method': "estimated"}
    model = SimpleExpSmoothing(ts, **kwargs)
    
    if alpha:
        fit_res = model.fit(smoothing_level=alpha, optimized=False)
    else:
        fit_res = model.fit()
        
    fitted = fit_res.fittedvalues
    forecast = fit_res.forecast(forecast_horizon)
    
    return fitted, forecast

def run_holt_winters(ts, seasonal_periods, forecast_horizon):
    """
    Runs Holt-Winters Seasonal Exponential Smoothing (Trend + Seasonality).
    We assume Additive trend and Additive seasonality for robustness with 0s.
    """
    # Need at least 2 full seasonal cycles for robust HW, but statsmodels can sometimes do with less.
    # We throw error if len < seasonal_periods * 2
    if len(ts) < seasonal_periods * 2:
        raise ValueError(f"Holt-Winters requires at least two full seasonal cycles ({seasonal_periods*2} periods). Given: {len(ts)}")
        
    model = ExponentialSmoothing(
        ts, 
        trend='add', 
        seasonal='add', 
        seasonal_periods=seasonal_periods,
        initialization_method="estimated"
    )
    fit_res = model.fit()
    
    fitted = fit_res.fittedvalues
    forecast = fit_res.forecast(forecast_horizon)
    
    return fitted, forecast

def generate_forecast_chart(ts, forecasts_dict, title):
    """
    Generates a Plotly HTML div for the forecast graph.
    `forecasts_dict` is a mapping: {"Method Name": pd.Series of future forecast}
    """
    fig = go.Figure()

    # Add Actual Data
    fig.add_trace(go.Scatter(
        x=ts.index, 
        y=ts.values,
        mode='lines+markers',
        name='Actual Sales',
        line=dict(color='black', width=3)
    ))

    # Define some nice colors for different methods
    colors = ['blue', 'orange', 'green', 'red', 'purple']
    
    # Add each forecast method line
    for i, (method_name, forecast_series) in enumerate(forecasts_dict.items()):
        
        # Connect the last actual point to the forecast for a contiguous line chart
        if not ts.empty and not forecast_series.empty:
            comb_x = [ts.index[-1]] + list(forecast_series.index)
            comb_y = [ts.values[-1]] + list(forecast_series.values)
        else:
            comb_x = forecast_series.index
            comb_y = forecast_series.values
            
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Scatter(
            x=comb_x, 
            y=comb_y,
            mode='lines+markers',
            name=f'{method_name} Forecast',
            line=dict(dash='dash', color=color, width=2)
        ))

    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Quantity',
        hovermode="x unified",
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Return HTML div without full html tree
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
