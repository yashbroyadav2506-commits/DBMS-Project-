"""
Reports blueprint providing analytical views, stored procedure reporting, and CSV data export.
"""
import io
import csv
import json
from flask import Blueprint, render_template, request, session, Response
from auth import login_required
from services import report_service, product_service

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    user_role = session.get('role', 'clerk')

    low_stock_items = product_service.get_low_stock_products()
    category_summaries = report_service.get_category_summary_view(role=user_role)
    monthly_sales = report_service.get_monthly_sales_view(role=user_role)
    customer_orders = report_service.get_customer_orders_view(role=user_role)
    charts = report_service.get_dashboard_charts(role=user_role)

    # Stored procedure filter test
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    proc_report = None
    if start_date and end_date:
        try:
            proc_report = report_service.get_sales_report_proc(start_date, end_date)
        except Exception:
            pass

    return render_template(
        'reports/index.html',
        low_stock_items=low_stock_items,
        category_summaries=category_summaries,
        monthly_sales=monthly_sales,
        customer_orders=customer_orders,
        charts_json=json.dumps(charts),
        proc_report=proc_report,
        start_date=start_date,
        end_date=end_date
    )

@reports_bp.route('/reports/export-monthly-csv')
@login_required
def export_monthly_csv():
    user_role = session.get('role', 'clerk')
    data = report_service.get_monthly_sales_view(role=user_role)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Sales Month', 'Total Orders', 'Items Sold', 'Revenue (INR)', 'Average Order Value (INR)'])

    for row in data:
        writer.writerow([
            row['sales_month'], row['total_orders'], row['total_items_sold'],
            f"{float(row['total_revenue']):.2f}", f"{float(row['avg_order_value']):.2f}"
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=monthly_sales_summary.csv'
    return response

@reports_bp.route('/reports/export-customers-csv')
@login_required
def export_customers_csv():
    user_role = session.get('role', 'clerk')
    data = report_service.get_customer_orders_view(role=user_role)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer ID', 'Customer Name', 'Phone', 'City', 'Completed Orders', 'Total Spent (INR)', 'Last Order Date'])

    for row in data:
        writer.writerow([
            row['customer_id'], row['customer_name'], row.get('phone') or 'N/A', row.get('city') or 'N/A',
            row['completed_orders'], f"{float(row['total_spent']):.2f}", str(row.get('last_order_date') or 'N/A')
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=customer_spending_summary.csv'
    return response
