import subprocess

mysql = r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
passwords = [
    '', 'root', 'admin', 'password', '1234', '12345', '123456', '1234567', '12345678', '123456789',
    'root123', 'Root123', 'Root@123', 'root@123', 'root1234', 'Root1234', 'root@1234',
    'mysql', 'MySQL', 'mysql123', 'MySQL123', 'MySQL@123', 'mysql@123', 'MySQL80', 'mysql80',
    'yash', 'Yash', 'yashyadav', 'YashYadav', 'yash2510', 'Yash2510', 'Yash@2510', 'yash@2510',
    'yash123', 'Yash123', 'Yash@123', 'yash@123', 'yash1234', 'Yash1234',
    'dbms', 'DBMS', 'dbms123', 'DBMS123', 'DBMS@123', 'Dbms@123', 'dbms@123',
    'sql', 'SQL', 'sql123', 'Sql123', 'Sql@123', 'welcome', 'welcome1', 'welcome123',
    'manager', 'manager123', 'clerk', 'clerk123', 'shop_manager', 'shop_clerk',
    'yash25', 'Yash25', 'Yash@25', 'yash@25', '25102004', '251004', '2510'
]

found = False
for p in passwords:
    cmd = [mysql, '-u', 'root'] if p == '' else [mysql, '-u', 'root', f'-p{p}']
    res = subprocess.run(cmd + ['-e', 'SHOW DATABASES;'], capture_output=True, text=True)
    if res.returncode == 0:
        print(f'*** SUCCESS! Root password is: "{p}" ***')
        print(res.stdout)
        found = True
        break

if not found:
    print('None of the listed passwords worked.')
