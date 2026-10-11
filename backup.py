"""
Database backup utility for grocery_shop_db.
Supports mysqldump and python-native SQL dump fallback.
"""
import os
import sys
import subprocess
from datetime import datetime
import mysql.connector
from config import Config

BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'sql', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def run_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f"backup_{Config.DB_NAME}_{timestamp}.sql")
    print(f"=== Starting Database Backup for '{Config.DB_NAME}' ===")

    # 1. Look for mysqldump binary
    mysqldump_candidates = [
        'mysqldump',
        r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
        r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe'
    ]
    dump_bin = None
    for candidate in mysqldump_candidates:
        try:
            res = subprocess.run([candidate, '--version'], capture_output=True, text=True)
            if res.returncode == 0:
                dump_bin = candidate
                break
        except Exception:
            continue

    if dump_bin:
        print(f"Using mysqldump binary: {dump_bin}")
        cmd = [
            dump_bin,
            f"--host={Config.DB_HOST}",
            f"--port={Config.DB_PORT}",
            f"--user={Config.MANAGER_DB_USER}",
            f"--password={Config.MANAGER_DB_PASS}",
            "--routines",
            "--triggers",
            Config.DB_NAME
        ]
        with open(backup_file, 'w', encoding='utf-8') as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0:
            print(f"[SUCCESS] Database successfully backed up to: {backup_file}")
            print(f"File size: {os.path.getsize(backup_file):,} bytes")
            return backup_file
        else:
            print(f"[WARN] mysqldump failed ({proc.stderr.strip()}), switching to python dump...")

    # 2. Python-native dump fallback
    print("Exporting database tables via Python connector...")
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.MANAGER_DB_USER,
        password=Config.MANAGER_DB_PASS,
        database=Config.DB_NAME
    )
    cursor = conn.cursor()

    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE';")
    tables = [r[0] for r in cursor.fetchall() if r[0] != 'schema_migrations']

    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Grocery Store Database Dump\n-- Date: {datetime.now().isoformat()}\n-- Database: {Config.DB_NAME}\n\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

        for table in tables:
            f.write(f"-- Table structure for `{table}`\n")
            cursor.execute(f"SHOW CREATE TABLE `{table}`;")
            create_stmt = cursor.fetchone()[1]
            f.write(f"DROP TABLE IF EXISTS `{table}`;\n{create_stmt};\n\n")

            cursor.execute(f"SELECT * FROM `{table}`;")
            rows = cursor.fetchall()
            if rows:
                col_names = [d[0] for d in cursor.description]
                cols_str = ", ".join([f"`{c}`" for c in col_names])
                f.write(f"-- Dumping data for table `{table}` ({len(rows)} rows)\n")
                f.write(f"INSERT INTO `{table}` ({cols_str}) VALUES\n")

                formatted_rows = []
                for row in rows:
                    vals = []
                    for v in row:
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            clean_str = str(v).replace("'", "''").replace("\\", "\\\\")
                            vals.append(f"'{clean_str}'")
                    formatted_rows.append(f"({', '.join(vals)})")

                f.write(",\n".join(formatted_rows) + ";\n\n")

        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")

    conn.close()
    print(f"[SUCCESS] Native backup completed: {backup_file}")
    print(f"File size: {os.path.getsize(backup_file):,} bytes")
    return backup_file

if __name__ == '__main__':
    run_backup()
