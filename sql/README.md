# SQL Server Security Demo Scripts

These scripts demonstrate the required chain:

`SQL Server LOGIN -> database USER -> database ROLE -> permissions`

They are text files for manual review and execution in SQL Server Management Studio (SSMS). The Python application does not create accounts or grant permissions.

## Before running anything

Edit and verify these values first:

1. Replace every `QLTV` database name if your database uses another name.
2. Confirm that `dbo.NHANVIEN` contains `MANV = 1` and `MANV = 2`.
3. If you want different employees, replace every login/user `[1]` and `[2]` with the corresponding numeric `MANV` values. Keep each SQL login name exactly equal to its `MANV`.
4. Replace `CHANGE_ME_Test1!` and `CHANGE_ME_Test2!` with passwords that satisfy your SQL Server password policy.
5. Make sure SQL Server Authentication (mixed mode) is enabled if your instance currently accepts Windows Authentication only.

## Run order in SSMS

1. Open and review `01_security_setup.sql`, then run it in SSMS against the intended instance. It creates `QLTV_MANAGER` and `QLTV_STAFF`. Both roles can read `dbo.NHANVIEN`; the manager can read the rest of the `dbo` schema for a visible permission comparison.
2. Open and edit `02_test_accounts.sql`, then run it manually. It creates two server logins, maps them to database users, and adds each user to one application role. Existing logins are not altered and passwords are not reset.
3. Open `03_verify_security.sql`. Its executable statements are read-only verification queries. Follow the manual test comments at the bottom while connected separately as Account A and Account B.

## Manual SSMS test

Connect with SQL Server Authentication as login `1`, select the `QLTV` database, and run verification sections E through H. Then disconnect completely and repeat with login `2`.

The expected difference is:

- Account A (`1` / `QLTV_MANAGER`) can select from `NHANVIEN` and `ISBN`.
- Account B (`2` / `QLTV_STAFF`) can select from `NHANVIEN`, but not `ISBN` unless a pre-existing grant already gives broader access.

The scripts deliberately do not use `DENY`, because an existing database may already have intentional permissions that should not be overridden.

## How the Python application uses the accounts

The login form sends the entered login name and password directly to SQL Server through `pyodbc`. After SQL Server authenticates the account, the application uses the same live connection to read `ORIGINAL_LOGIN()`, `SUSER_SNAME()`, `USER_NAME()`, role membership, and the matching `NHANVIEN` row.

Because the existing schema defines `MANV` as an integer and has no login-name column, the demo uses a numeric SQL login name equal to `MANV`. No password is stored in `NHANVIEN`, no account table is added, and the application never reconnects as `sa` or another administrator.

