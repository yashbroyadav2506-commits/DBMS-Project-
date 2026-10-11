from flask import Blueprint, render_template, request, flash, session
from auth import login_required, role_required
from db import get_db
from services.admin_service import log_audit
import mysql.connector

schema_alter_bp = Blueprint('schema_alter', __name__)

ALLOWED_TABLES = {'product'}
ALLOWED_COLUMNS = {'discount_pct', 'reorder_level'}

PREAPPROVED_OPERATIONS = {
    'add_discount': {
        'label': 'Add Column: discount_pct DECIMAL(5,2) DEFAULT 0.00 to product table',
        'sql': 'ALTER TABLE product ADD COLUMN discount_pct DECIMAL(5,2) DEFAULT 0.00;',
        'table': 'product',
        'column': 'discount_pct'
    },
    'modify_reorder': {
        'label': 'Modify Column: reorder_level INT DEFAULT 15 in product table',
        'sql': 'ALTER TABLE product MODIFY COLUMN reorder_level INT DEFAULT 15;',
        'table': 'product',
        'column': 'reorder_level'
    },
    'drop_discount': {
        'label': 'Drop Column: discount_pct from product table',
        'sql': 'ALTER TABLE product DROP COLUMN discount_pct;',
        'table': 'product',
        'column': 'discount_pct'
    }
}

@schema_alter_bp.route('/schema-alter', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def index():
    conn = get_db('manager')
    cursor = conn.cursor(dictionary=True)

    executed_op = None
    executed_sql = None

    if request.method == 'POST':
        op_key = request.form.get('operation', '').strip()
        if op_key in PREAPPROVED_OPERATIONS:
            op_info = PREAPPROVED_OPERATIONS[op_key]
            
            # Whitelist checks
            if op_info['table'] not in ALLOWED_TABLES or op_info['column'] not in ALLOWED_COLUMNS:
                flash("Security Error: Whitelist validation failed for table or column!", "danger")
            else:
                try:
                    cursor.execute(op_info['sql'])
                    conn.commit()
                    executed_op = op_info['label']
                    executed_sql = op_info['sql']
                    log_audit('product', 'ALTER_SCHEMA', None, None, op_info['label'], session.get('username', 'manager'))
                    flash(f"Schema alteration executed successfully: {op_info['label']}", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"ALTER operation error: {err.msg}", "danger")
        else:
            flash("Invalid or unapproved operation selected.", "danger")

    # Get current DESCRIBE output for Product table
    cursor.execute("DESCRIBE product;")
    describe_output = cursor.fetchall()

    return render_template(
        'schema_alter/index.html',
        operations=PREAPPROVED_OPERATIONS,
        describe_output=describe_output,
        executed_op=executed_op,
        executed_sql=executed_sql
    )
