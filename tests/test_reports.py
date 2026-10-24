import logging
from unittest.mock import Mock

import mysql.connector

from services import product_service, report_service


def test_sales_procedure_database_error_is_reported(client, monkeypatch, caplog):
    monkeypatch.setattr(product_service, 'get_low_stock_products', Mock(return_value=[]))
    monkeypatch.setattr(report_service, 'get_category_summary_view', Mock(return_value=[]))
    monkeypatch.setattr(report_service, 'get_monthly_sales_view', Mock(return_value=[]))
    monkeypatch.setattr(report_service, 'get_customer_orders_view', Mock(return_value=[]))
    monkeypatch.setattr(report_service, 'get_dashboard_charts', Mock(return_value={}))
    monkeypatch.setattr(
        report_service,
        'get_sales_report_proc',
        Mock(side_effect=mysql.connector.Error("procedure unavailable")),
    )
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'manager'
        session['username'] = 'manager_user'

    caplog.set_level(logging.ERROR, logger='grocery_app')
    response = client.get('/reports?start_date=2026-10-01&end_date=2026-10-12')

    assert response.status_code == 200
    assert b"sales report could not be generated" in response.data
    assert "Stored procedure sp_sales_report failed: procedure unavailable" in caplog.text
