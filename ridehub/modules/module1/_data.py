"""
Dashboard data loading: SQL queries for KPI, status, payment, vehicle,
daily, and top-vehicle metrics.
"""
from datetime import datetime, timedelta
from data.uber import get_db_connection


def load_dashboard_data(start_date, end_date):
    """Return a dict with all dashboard metrics for the given date range."""
    conn = get_db_connection()
    if not conn:
        return {}
    cursor = conn.cursor(dictionary=True)
    date_filter, params = "", []
    if start_date and end_date:
        date_filter = "WHERE `Date` BETWEEN %s AND %s"
        params = [start_date, end_date]

    prev_params, prev_filter = [], ""
    if start_date and end_date:
        try:
            s = datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.strptime(end_date, "%Y-%m-%d")
            delta = e - s
            pe = s - timedelta(days=1)
            ps = pe - delta
            prev_filter = "WHERE `Date` BETWEEN %s AND %s"
            prev_params = [ps.strftime("%Y-%m-%d"), pe.strftime("%Y-%m-%d")]
        except Exception:
            pass

    cursor.execute(
        f"SELECT COUNT(*) as total, SUM(`Booking Value`) as revenue, "
        f"AVG(`Driver Ratings`) as avg_rate, AVG(`Avg VTAT`) as avg_vtat "
        f"FROM rides {date_filter}", params)
    kpi = cursor.fetchone()
    cursor.execute(
        f"SELECT COUNT(*) as cnt FROM rides {date_filter}"
        f"{' AND' if date_filter else ' WHERE'} `Booking Status`='Completed'", params)
    completed = cursor.fetchone()['cnt']

    total = int(kpi['total'] or 0)
    revenue = float(kpi['revenue'] or 0)
    avg_rate = float(kpi['avg_rate'] or 0)
    avg_vtat = float(kpi['avg_vtat'] or 0)
    completion_rate = (completed / total * 100) if total > 0 else 0
    avg_rev_per_ride = (revenue / total) if total > 0 else 0

    prev_kpi = {"total": 0, "revenue": 0}
    if prev_params:
        try:
            cursor.execute(
                f"SELECT COUNT(*) as total, SUM(`Booking Value`) as revenue "
                f"FROM rides {prev_filter}", prev_params)
            row = cursor.fetchone()
            if row:
                prev_kpi = row
        except Exception:
            pass

    cursor.execute(
        f"SELECT `Booking Status`, COUNT(*) as cnt FROM rides {date_filter} "
        f"GROUP BY `Booking Status`", params)
    status_dist = {r['Booking Status']: r['cnt'] for r in cursor.fetchall()}

    payment_dist, vehicle_rev, daily_data, top_vehicles = {}, [], [], []
    try:
        cursor.execute(
            f"SELECT `Payment Method`, COUNT(*) as cnt FROM rides {date_filter} "
            f"GROUP BY `Payment Method`", params)
        payment_dist = {r['Payment Method']: r['cnt'] for r in cursor.fetchall()}
        cursor.execute(
            f"SELECT `Vehicle Type`, SUM(`Booking Value`) as rev FROM rides {date_filter} "
            f"GROUP BY `Vehicle Type` ORDER BY rev DESC", params)
        vehicle_rev = cursor.fetchall()
        cursor.execute(
            f"SELECT `Date`, COUNT(*) as total_rides, SUM(`Booking Value`) as revenue, "
            f"AVG(`Driver Ratings`) as avg_rating, "
            f"SUM(CASE WHEN `Booking Status`='Completed' THEN 1 ELSE 0 END) as completed, "
            f"SUM(CASE WHEN `Booking Status` LIKE '%Cancel%' OR `Booking Status`='Incomplete' "
            f"THEN 1 ELSE 0 END) as cancellations "
            f"FROM rides {date_filter} GROUP BY `Date` ORDER BY `Date`", params)
        daily_data = cursor.fetchall()
        cursor.execute(
            f"SELECT `Vehicle Type`, COUNT(*) as total_rides, "
            f"SUM(`Booking Value`) as total_revenue, "
            f"AVG(`Booking Value`) as avg_rev_per_ride, "
            f"AVG(`Driver Ratings`) as avg_rating, "
            f"SUM(CASE WHEN `Booking Status`='Completed' THEN 1 ELSE 0 END)/COUNT(*)*100 "
            f"as completion_rate "
            f"FROM rides {date_filter} GROUP BY `Vehicle Type` ORDER BY total_revenue DESC",
            params)
        top_vehicles = cursor.fetchall()
    except Exception:
        pass
    conn.close()
    return {
        "total": total, "revenue": revenue, "avg_rate": avg_rate,
        "avg_vtat": avg_vtat, "completion_rate": completion_rate,
        "avg_rev_per_ride": avg_rev_per_ride,
        "prev_total": int(prev_kpi.get("total") or 0),
        "prev_revenue": float(prev_kpi.get("revenue") or 0),
        "status_dist": status_dist, "payment_dist": payment_dist,
        "vehicle_rev": vehicle_rev, "daily_data": daily_data,
        "top_vehicles": top_vehicles,
    }
