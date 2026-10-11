"""
Supplier and Brand management service module.
"""
from typing import List, Dict, Any, Optional
import mysql.connector
from db import get_db_cursor
from services.admin_service import log_audit

# --- Suppliers ---

def get_all_suppliers(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches all suppliers along with the count of products supplied.
    """
    with get_db_cursor(role) as (conn, cursor):
        sql = """
            SELECT s.supplier_id, s.name, s.phone, s.email,
                   COUNT(p.product_id) AS product_count
            FROM supplier s
            LEFT JOIN product p ON s.supplier_id = p.supplier_id AND p.is_active = 1
            GROUP BY s.supplier_id, s.name, s.phone, s.email
            ORDER BY s.name ASC;
        """
        cursor.execute(sql)
        return cursor.fetchall()

def get_supplier_by_id(supplier_id: int, role: str = 'manager') -> Optional[Dict[str, Any]]:
    with get_db_cursor(role) as (conn, cursor):
        cursor.execute("SELECT supplier_id, name, phone, email FROM supplier WHERE supplier_id = %s;", (supplier_id,))
        return cursor.fetchone()

def add_supplier(name: str, phone: str, email: str, changed_by: str = 'manager') -> int:
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute(
            "INSERT INTO supplier (name, phone, email) VALUES (%s, %s, %s);",
            (name.strip(), phone.strip() or None, email.strip() or None)
        )
        supplier_id = cursor.lastrowid
    log_audit('supplier', 'INSERT', supplier_id, None, f"name: {name}, phone: {phone}, email: {email}", changed_by)
    return supplier_id

def update_supplier(supplier_id: int, name: str, phone: str, email: str, changed_by: str = 'manager'):
    old = get_supplier_by_id(supplier_id)
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute(
            "UPDATE supplier SET name = %s, phone = %s, email = %s WHERE supplier_id = %s;",
            (name.strip(), phone.strip() or None, email.strip() or None, supplier_id)
        )
    old_desc = f"name: {old['name']}" if old else ""
    log_audit('supplier', 'UPDATE', supplier_id, old_desc, f"name: {name}", changed_by)

def delete_supplier(supplier_id: int, changed_by: str = 'manager'):
    old = get_supplier_by_id(supplier_id)
    try:
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("DELETE FROM supplier WHERE supplier_id = %s;", (supplier_id,))
        if old:
            log_audit('supplier', 'DELETE', supplier_id, f"name: {old['name']}", None, changed_by)
    except mysql.connector.Error as err:
        if err.errno == 1451:
            raise ValueError("Cannot delete this supplier because active products reference it.")
        raise err

# --- Brands ---

def get_all_brands(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches all brands along with product count.
    """
    with get_db_cursor(role) as (conn, cursor):
        sql = """
            SELECT b.brand_id, b.brand_name,
                   COUNT(p.product_id) AS product_count
            FROM brand b
            LEFT JOIN product p ON b.brand_id = p.brand_id AND p.is_active = 1
            GROUP BY b.brand_id, b.brand_name
            ORDER BY b.brand_name ASC;
        """
        cursor.execute(sql)
        return cursor.fetchall()

def get_brand_by_id(brand_id: int, role: str = 'manager') -> Optional[Dict[str, Any]]:
    with get_db_cursor(role) as (conn, cursor):
        cursor.execute("SELECT brand_id, brand_name FROM brand WHERE brand_id = %s;", (brand_id,))
        return cursor.fetchone()

def add_brand(brand_name: str, changed_by: str = 'manager') -> int:
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("INSERT INTO brand (brand_name) VALUES (%s);", (brand_name.strip(),))
        brand_id = cursor.lastrowid
    log_audit('brand', 'INSERT', brand_id, None, f"brand_name: {brand_name}", changed_by)
    return brand_id

def update_brand(brand_id: int, brand_name: str, changed_by: str = 'manager'):
    old = get_brand_by_id(brand_id)
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE brand SET brand_name = %s WHERE brand_id = %s;", (brand_name.strip(), brand_id))
    old_desc = f"name: {old['brand_name']}" if old else ""
    log_audit('brand', 'UPDATE', brand_id, old_desc, f"name: {brand_name}", changed_by)

def delete_brand(brand_id: int, changed_by: str = 'manager'):
    old = get_brand_by_id(brand_id)
    try:
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("DELETE FROM brand WHERE brand_id = %s;", (brand_id,))
        if old:
            log_audit('brand', 'DELETE', brand_id, f"name: {old['brand_name']}", None, changed_by)
    except mysql.connector.Error as err:
        if err.errno == 1451:
            raise ValueError("Cannot delete this brand because active products reference it.")
        raise err
