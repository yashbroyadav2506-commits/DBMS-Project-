"""
Dashboard blueprint providing KPI metric cards, Chart.js visualizations, low-stock manager banner, and global search.
"""
import json
from flask import Blueprint, render_template, request, session
from auth import login_required
from services import report_service, order_service, product_service, customer_service

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    user_role = session.get('role', 'clerk')

    kpis = report_service.get_dashboard_kpis(role=user_role)
    charts = report_service.get_dashboard_charts(role=user_role)
    recent_orders, _, _ = order_service.get_orders(page=1, per_page=6, role=user_role)
    low_stock_products = product_service.get_low_stock_products() if user_role == 'manager' else []

    return render_template(
        'dashboard.html',
        kpis=kpis,
        charts=charts,
        charts_json=json.dumps(charts),
        recent_orders=recent_orders,
        low_stock_products=low_stock_products
    )

@dashboard_bp.route('/search')
@login_required
def global_search():
    """
    Unified global search bar across products, customers, and orders.
    """
    user_role = session.get('role', 'clerk')
    query = request.args.get('q', '').strip()

    products = []
    customers = []
    orders = []

    if query:
        products, _, _ = product_service.get_products(search_query=query, page=1, per_page=10, role=user_role)
        customers = customer_service.get_customers(search_query=query, role=user_role)[:10]
        orders, _, _ = order_service.get_orders(search_query=query, page=1, per_page=10, role=user_role)

    return render_template(
        'search_results.html',
        query=query,
        products=products,
        customers=customers,
        orders=orders
    )
