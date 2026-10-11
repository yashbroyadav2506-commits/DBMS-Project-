import subprocess
import time
import os

init_file = r'C:\Users\Yash Yadav\AppData\Local\Temp\mysql-init.txt'
with open(init_file, 'w') as f:
    f.write("ALTER USER 'root'@'localhost' IDENTIFIED BY 'root';\nFLUSH PRIVILEGES;\n")

print('Stopping MySQL80 service...')
res_stop = subprocess.run(['net', 'stop', 'MySQL80'], capture_output=True, text=True)
print('Stop output:', res_stop.stdout, res_stop.stderr)

print('Running mysqld with init file...')
mysqld = r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'
proc = subprocess.Popen([mysqld, r'--defaults-file=C:\ProgramData\MySQL\MySQL Server 8.0\my.ini', f'--init-file={init_file}'])
time.sleep(6)
proc.terminate()
try:
    proc.wait(timeout=3)
except Exception:
    proc.kill()

print('Starting MySQL80 service...')
res_start = subprocess.run(['net', 'start', 'MySQL80'], capture_output=True, text=True)
print('Start output:', res_start.stdout, res_start.stderr)

# Test connection
mysql = r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
res_test = subprocess.run([mysql, '-u', 'root', '-proot', '-e', 'SHOW DATABASES;'], capture_output=True, text=True)
print('Test result returncode:', res_test.returncode)
print('Test stdout:', res_test.stdout)
print('Test stderr:', res_test.stderr)
