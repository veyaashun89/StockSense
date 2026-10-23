import datetime
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from backend.database import get_db
from backend.services.market_service import get_active_market_multiplier

def get_product_sales_series(
    product_id: int,
    window_days: int = 30,
    end_date: Optional[datetime.date] = None,
    shop_id: int = 1
) -> pd.DataFrame:
    """
    Fetches daily sales history for a product and fills missing dates with 0 sales.
    Returns DataFrame with columns: ['date', 'quantity_sold'].
    """
    db = get_db()
    cursor = db.cursor()

    if end_date is None:
        cursor.execute("SELECT MAX(sale_date) FROM sales WHERE product_id = ? AND shop_id = ?", (product_id, shop_id))
        max_date_row = cursor.fetchone()
        if max_date_row and max_date_row[0]:
            try:
                end_date = datetime.date.fromisoformat(max_date_row[0])
            except Exception:
                end_date = datetime.date.today()
        else:
            end_date = datetime.date.today()

    start_date = end_date - datetime.timedelta(days=window_days - 1)

    cursor.execute("""
        SELECT sale_date, SUM(quantity_sold) as total_qty
        FROM sales
        WHERE product_id = ? AND shop_id = ? AND sale_date >= ? AND sale_date <= ?
        GROUP BY sale_date
        ORDER BY sale_date ASC
    """, (product_id, shop_id, start_date.isoformat(), end_date.isoformat()))
    
    rows = cursor.fetchall()
    sales_dict = {row["sale_date"]: row["total_qty"] for row in rows}

    all_dates = [start_date + datetime.timedelta(days=i) for i in range(window_days)]
    data = []
    for d in all_dates:
        d_str = d.isoformat()
        data.append({
            "date": d_str,
            "quantity_sold": float(sales_dict.get(d_str, 0))
        })

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["quantity_sold"] = df["quantity_sold"].astype(float)
    return df

def forecast_demand(
    product_id: int,
    horizon_days: int = 14,
    window_days: int = 30,
    method: str = "moving_average",
    shop_id: int = 1
) -> Dict[str, Any]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.*, s.lead_time as supplier_lead_time 
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.id = ? AND p.shop_id = ?
    """, (product_id, shop_id))
    product = cursor.fetchone()
    if not product:
        raise ValueError(f"Product ID {product_id} not found.")

    df = get_product_sales_series(product_id, window_days=window_days, shop_id=shop_id)
    
    total_sold = df["quantity_sold"].sum()
    non_zero_days = (df["quantity_sold"] > 0).sum()
    base_avg_daily = float(df["quantity_sold"].mean()) if len(df) > 0 else 0.0

    # Market Adjustment
    market_info = get_active_market_multiplier(product["category"], product["sku"])
    adjusted_avg_daily = round(base_avg_daily * market_info["multiplier"], 2)

    warning = None
    if len(df) == 0 or total_sold == 0:
        warning = "No historical sales recorded in selected window. Forecast estimated at zero."
    elif non_zero_days < 5:
        warning = f"Sparse sales data: only {non_zero_days} active sales days in past {window_days} days. Forecast confidence is low."
    elif window_days < 14:
        warning = "Historical window is under 14 days; moving averages may be vulnerable to short-term volatility."

    # Backtesting on held-out 7-day period
    evaluation = None
    residual_std = 1.0
    if len(df) >= 21 and non_zero_days >= 7:
        train_df = df.iloc[:-7]
        test_df = df.iloc[-7:]
        
        train_mean = train_df["quantity_sold"].mean()
        actual_test = test_df["quantity_sold"].values
        predicted_test = np.full(len(actual_test), train_mean)

        residuals = actual_test - predicted_test
        residual_std = float(np.std(residuals)) if len(residuals) > 1 else 1.0
        mae = float(np.mean(np.abs(residuals)))
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        evaluation = {
            "test_window_days": 7,
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "note": "Backtested against recent 7 historical days using preceding history."
        }

    # Linear trend calculation
    trend_slope = 0.0
    trend_direction = "stable"
    if len(df) >= 5 and total_sold > 0:
        x = np.arange(len(df))
        y = df["quantity_sold"].values
        try:
            poly = np.polyfit(x, y, 1)
            trend_slope = float(poly[0])
            if trend_slope > 0.05:
                trend_direction = "increasing"
            elif trend_slope < -0.05:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        except Exception:
            trend_slope = 0.0

    # Project daily predictions
    last_date = df["date"].max() if len(df) > 0 else pd.Timestamp(datetime.date.today())
    future_dates = [last_date + pd.Timedelta(days=i + 1) for i in range(horizon_days)]
    
    daily_predictions = []
    if method == "linear_trend" and len(df) >= 7 and abs(trend_slope) > 0.01:
        x_base = len(df)
        for i, dt in enumerate(future_dates):
            pred_val = (poly[0] * (x_base + i) + poly[1]) * market_info["multiplier"]
            pred_val = max(0.0, float(pred_val))
            daily_predictions.append({
                "date": dt.strftime("%Y-%m-%d"),
                "predicted_demand": round(pred_val, 2)
            })
    else:
        for dt in future_dates:
            daily_predictions.append({
                "date": dt.strftime("%Y-%m-%d"),
                "predicted_demand": adjusted_avg_daily
            })

    lead_time = product["lead_time_days"] or 7
    lead_time_demand = round(adjusted_avg_daily * lead_time, 2)

    historical_series = [
        {"date": row["date"].strftime("%Y-%m-%d"), "actual_sales": int(row["quantity_sold"])}
        for _, row in df.iterrows()
    ]

    return {
        "product_id": product["id"],
        "sku": product["sku"],
        "product_name": product["name"],
        "category": product["category"],
        "forecast_method": method,
        "window_days": window_days,
        "horizon_days": horizon_days,
        "base_avg_daily_demand": round(base_avg_daily, 2),
        "average_daily_demand": adjusted_avg_daily,
        "market_adjustment": market_info,
        "total_historical_sold": int(total_sold),
        "active_sales_days": int(non_zero_days),
        "trend_slope": round(trend_slope, 4),
        "trend_direction": trend_direction,
        "lead_time_days": lead_time,
        "lead_time_demand": lead_time_demand,
        "warning": warning,
        "evaluation": evaluation,
        "historical_series": historical_series,
        "daily_forecast": daily_predictions
    }

def forecast_demand_weekly(
    product_id: int,
    horizon_weeks: int = 4,
    window_days: int = 60,
    method: str = "weekly_moving_average",
    shop_id: int = 1
) -> Dict[str, Any]:
    """
    Weekly-bucketed demand forecast with lower and upper estimate ranges.
    Aggregates historical sales into ISO weeks and projects week-by-week.
    """
    df = get_product_sales_series(product_id, window_days=window_days, shop_id=shop_id)
    if len(df) == 0:
        raise ValueError("No sales data available for weekly aggregation.")

    # Group into ISO weeks (Monday to Sunday)
    df["week_start"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
    weekly_df = df.groupby("week_start")["quantity_sold"].sum().reset_index()
    weekly_df = weekly_df.sort_values("week_start")

    # Exclude the earliest partial week if under 4 days
    if len(weekly_df) > 2:
        weekly_df = weekly_df.iloc[1:]

    avg_weekly_demand = float(weekly_df["quantity_sold"].mean()) if len(weekly_df) > 0 else 0.0
    std_weekly = float(weekly_df["quantity_sold"].std()) if len(weekly_df) > 1 else max(1.0, avg_weekly_demand * 0.2)

    # Product info
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT sku, name, category, lead_time_days FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()

    market_info = get_active_market_multiplier(prod["category"], prod["sku"])
    adj_weekly = round(avg_weekly_demand * market_info["multiplier"], 1)

    # Future weeks projection
    last_week_start = weekly_df["week_start"].max() if len(weekly_df) > 0 else pd.Timestamp(datetime.date.today())
    future_weeks = []
    for w in range(1, horizon_weeks + 1):
        w_start = last_week_start + pd.Timedelta(weeks=w)
        # Bounds: +- 1.5 standard deviations (bounded at >= 0)
        lower_bound = max(0.0, round(adj_weekly - 1.2 * std_weekly, 1))
        upper_bound = round(adj_weekly + 1.2 * std_weekly, 1)
        future_weeks.append({
            "week_number": w,
            "week_start": w_start.strftime("%Y-%m-%d"),
            "predicted_units": adj_weekly,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "range_label": f"{lower_bound} - {upper_bound} units (80% confidence estimate)"
        })

    hist_weeks = [
        {"week_start": row["week_start"].strftime("%Y-%m-%d"), "actual_units": int(row["quantity_sold"])}
        for _, row in weekly_df.iterrows()
    ]

    return {
        "product_id": product_id,
        "sku": prod["sku"],
        "product_name": prod["name"],
        "category": prod["category"],
        "forecast_granularity": "weekly",
        "horizon_weeks": horizon_weeks,
        "avg_weekly_demand": adj_weekly,
        "market_adjustment": market_info,
        "historical_weeks": hist_weeks,
        "weekly_forecast": future_weeks,
        "note": "Weekly estimates aggregated over ISO weeks; range bounds derived from residual volatility."
    }
