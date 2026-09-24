# QLTV Login Demo Setup Guide for Windows

This guide sets up branch `v02` on another Windows laptop where SQL Server Database Engine and SQL Server Management Studio are already installed. The setup keeps authentication in SQL Server: the Python application does not store passwords and does not use an application account table.

## What is and is not transferred by Git

Pulling the branch downloads the Python application and SQL scripts. It does not transfer:

- the `QLTV` database or its data;
- SQL Server logins and database users;
- SQL Server authentication-mode settings;
- Python or `pyodbc`;
- Microsoft ODBC Driver 18 for SQL Server.

Complete the package setup and SQL Server setup below before starting the application.

## 1. Download branch v02

For a new clone:

```powershell
git clone -b v02 https://github.com/kaffeinesloth/DB-Management-Project.git
cd DB-Management-Project
```

For an existing clone:

```powershell
git fetch origin
git switch v02
git pull --ff-only origin v02
```

## 2. Install missing runtime packages automatically

Open PowerShell in the repository root and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

The execution-policy change applies only to the current PowerShell window.

The script checks and, when necessary, installs:

- Python 3.12 through Windows Package Manager;
- Python dependencies from `official_app\requirements.txt`;
- Microsoft ODBC Driver 18 for SQL Server through Windows Package Manager.

The script also verifies `tkinter`, `pyodbc`, and the application imports. It does not connect to SQL Server, change SQL Server settings, execute SQL scripts, or store passwords. A Windows UAC prompt may appear when the ODBC driver is installed.

If the script reports that `winget` is unavailable, install or update **App Installer** from Microsoft Store and run the script again.

## 3. Identify the SQL Server instance name

Open SSMS and look at the **Server name** used by the working connection.

Common values are:

```text
localhost
localhost\SQLEXPRESS
COMPUTER-NAME
COMPUTER-NAME\SQLEXPRESS
```

Open `official_app\config.py` and set the same instance name:

```python
SQL_SERVER = "localhost"
DATABASE = "QLTV"
DRIVER = "ODBC Driver 18 for SQL Server"
```

For a named instance, use a raw Python string:

```python
SQL_SERVER = r"localhost\SQLEXPRESS"
```

Do not put a login name or password in `config.py`.

## 4. Enable SQL Server Authentication

The demo accounts are SQL Server logins, so the instance must use Mixed Mode Authentication.

In SSMS:

1. Connect with Windows Authentication using an administrator account.
2. Right-click the server in Object Explorer and select **Properties**.
3. Select **Security**.
4. Select **SQL Server and Windows Authentication mode**.
5. Apply the change.
6. Restart the SQL Server service.

This is an instance-wide setting. Do not change it on a managed university or workplace server without the server owner's approval.

## 5. Prepare the QLTV database

Choose the matching path below.

### Fresh laptop with no QLTV database

Open `beta_testing_files\QLTV_11_tables (1).sql` in SSMS and run it once.

Warning: that supplied schema script contains `DROP TABLE IF EXISTS` so it can rebuild the project during development. Use it only for a fresh database. Do not run it against a populated `QLTV` database whose data must be preserved.

After the 11 tables are created, add the two employees:

```sql
USE [QLTV];
GO

IF EXISTS (SELECT 1 FROM dbo.NHANVIEN)
BEGIN
    THROW 51030, 'NHANVIEN is not empty. Review existing MANV values instead of inserting demo employees.', 1;
END;
GO

INSERT INTO dbo.NHANVIEN
    (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL)
VALUES
    (N'Nguyễn Trọng', N'Hoàng', 1, N'Hà Nội',
     '0987654321', 'admin@qltv.com'),
    (N'Trần Thị', N'Mai', 0, N'Hà Nội',
     '0976543210', 'mai.tt@qltv.com');
GO

SELECT MANV, HONV, TENNV, EMAIL
FROM dbo.NHANVIEN
ORDER BY MANV;
```

On a fresh database, the two employees should receive `MANV` 1 and 2.

Do not run `beta_testing_files\insert_sample_data.sql` for the login demo. It belongs to the older beta implementation and adds a local password column that conflicts with SQL Server authentication.

### Laptop with an existing QLTV database

Do not run the reset-style schema script. Inspect the existing employees instead:

```sql
USE [QLTV];
GO

SELECT MANV, HONV, TENNV, EMAIL
FROM dbo.NHANVIEN
ORDER BY MANV;
```

Choose two existing `MANV` values. In `sql\02_test_accounts.sql`, replace database users `[1]` and `[2]` with those numeric employee IDs. The readable server login names can be changed independently.

## 6. Create roles, logins, users, and permissions

Run the official scripts manually in SSMS in this order:

1. `sql\01_security_setup.sql`
2. `sql\02_test_accounts.sql`
3. `sql\03_verify_security.sql`

Before running `02_test_accounts.sql`, replace:

```text
CHANGE_ME_Test1!
CHANGE_ME_Test2!
```

with new passwords that satisfy the SQL Server password policy. Do not commit the real passwords to Git.

With the default employee IDs, the security mapping is:

```text
SQL login:      nguyen_trong_hoang
Database user:  1
Employee:       MANV 1 - Nguyễn Trọng Hoàng
Database role:  QLTV_MANAGER
```

```text
SQL login:      tran_thi_mai
Database user:  2
Employee:       MANV 2 - Trần Thị Mai
Database role:  QLTV_STAFF
```

Use `03_verify_security.sql` to confirm both identities and their different permissions. The manager should be able to read `dbo.ISBN`; the staff account should not, unless another pre-existing grant provides that access.

## 7. Run the application

From the repository root:

```powershell
python official_app\main.py
```

Enter one of the readable SQL login names and the password assigned in `02_test_accounts.sql`.

After authentication, the main window should display:

- employee ID and full name;
- authenticated SQL login;
- mapped database user;
- database role membership.

Use **Logout** to close the authenticated database connection and return to a cleared, enabled login form.

## Troubleshooting

### No module named pyodbc

Run:

```powershell
.\setup_windows.ps1
```

### Data source name not found or driver not specified

Check the installed driver list:

```powershell
python -c "import pyodbc; print(pyodbc.drivers())"
```

Confirm that `official_app\config.py` uses a driver name from that list.

### Login failed with SQL Server error 18456

Check that:

- Mixed Mode Authentication is enabled;
- SQL Server was restarted after enabling Mixed Mode;
- the login was created by `02_test_accounts.sql`;
- the login name and password are entered exactly and passwords retain their original capitalization.

### Cannot open database QLTV

Confirm that `QLTV` exists, the database user was created, and `DATABASE = "QLTV"` is set in `config.py`.

### Application cannot find the employee

The numeric database user must match an existing `NHANVIEN.MANV`. Review the role and user mapping in `02_test_accounts.sql` and the employee records in `QLTV.dbo.NHANVIEN`.

