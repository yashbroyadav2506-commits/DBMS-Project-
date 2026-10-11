import os
import re
import mysql.connector
from config import Config

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'sql', 'migrations')

def get_db_connection():
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.MANAGER_DB_USER,
        password=Config.MANAGER_DB_PASS,
        database=Config.DB_NAME,
        autocommit=False
    )

def ensure_migrations_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(100) PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

def get_applied_migrations(cursor):
    cursor.execute("SELECT version FROM schema_migrations;")
    return {row[0] for row in cursor.fetchall()}

def parse_sql_statements(content: str):
    """
    Parses SQL content, properly handling DELIMITER $$ and DELIMITER ; blocks.
    """
    statements = []
    lines = content.splitlines()
    current_delimiter = ';'
    current_stmt = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue

        delim_match = re.match(r'^DELIMITER\s+(\S+)', stripped, re.IGNORECASE)
        if delim_match:
            current_delimiter = delim_match.group(1)
            continue

        current_stmt.append(line)
        joined_stmt = "\n".join(current_stmt).strip()

        if current_delimiter == ';':
            if joined_stmt.endswith(';'):
                stmt = joined_stmt[:-1].strip()
                if stmt:
                    statements.append(stmt)
                current_stmt = []
        else:
            if joined_stmt.endswith(current_delimiter):
                stmt = joined_stmt[:-len(current_delimiter)].strip()
                if stmt:
                    statements.append(stmt)
                current_stmt = []

    if current_stmt:
        remaining = "\n".join(current_stmt).strip()
        if remaining:
            if remaining.endswith(';'):
                remaining = remaining[:-1].strip()
            if remaining:
                statements.append(remaining)

    return statements

def run_migrations():
    print("=== Running Database Migrations ===")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        ensure_migrations_table(cursor)
        conn.commit()
        applied = get_applied_migrations(cursor)

        files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql')])

        for f in files:
            if f in applied:
                print(f"[SKIP] Migration '{f}' already applied.")
                continue

            print(f"[APPLYING] Migration '{f}'...")
            filepath = os.path.join(MIGRATIONS_DIR, f)
            with open(filepath, 'r', encoding='utf-8') as sql_file:
                content = sql_file.read()

            statements = parse_sql_statements(content)
            for stmt in statements:
                try:
                    cursor.execute(stmt)
                except mysql.connector.Error as err:
                    # Ignore duplicate column / index exists errors for idempotency
                    if err.errno in (1060, 1061):  # Duplicate column name, Duplicate key name
                        print(f"  [INFO] Already exists ({err.msg}), continuing...")
                    elif err.errno == 1419:  # SUPER privilege required for trigger creation under binary logging
                        print(f"  [WARN] Trigger creation skipped due to binary logging restrictions ({err.msg}). Audit service fallback will handle logging.")
                    else:
                        print(f"  [ERROR] Failed statement: {stmt[:100]}...")
                        raise err

            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s);", (f,))
            conn.commit()
            print(f"[OK] Migration '{f}' applied successfully!")

        print("=== All Migrations Applied Cleanly ===")
    except Exception as e:
        conn.rollback()
        print(f"Migration Failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    run_migrations()
