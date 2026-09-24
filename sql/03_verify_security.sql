/*
    Library Management security demo - read-only verification queries

    This file contains SELECT statements only. Run sections as indicated.
    If your database is not named QLTV, replace [QLTV] below.
*/

/* A. Server logins (run with an account allowed to view server principals). */
USE [master];
GO

SELECT
    [name] AS [sql_login],
    [type_desc],
    [is_disabled],
    [create_date]
FROM sys.server_principals
WHERE [name] IN (N'nguyen_trong_hoang', N'tran_thi_mai')
ORDER BY [name];
GO

/* B. Database users. */
USE [QLTV];
GO

SELECT
    [name] AS [database_user],
    [type_desc],
    [authentication_type_desc],
    [create_date]
FROM sys.database_principals
WHERE [name] IN (N'1', N'2')
ORDER BY [name];
GO

/* C. Application roles. */
SELECT
    [name] AS [database_role],
    [type_desc],
    [is_fixed_role]
FROM sys.database_principals
WHERE [type] = 'R'
  AND [name] IN (N'QLTV_MANAGER', N'QLTV_STAFF')
ORDER BY [name];
GO

/* D. Role memberships. */
SELECT
    role_principal.[name] AS [database_role],
    member_principal.[name] AS [database_user]
FROM sys.database_role_members AS membership
INNER JOIN sys.database_principals AS role_principal
    ON role_principal.[principal_id] = membership.[role_principal_id]
INNER JOIN sys.database_principals AS member_principal
    ON member_principal.[principal_id] = membership.[member_principal_id]
WHERE role_principal.[name] IN (N'QLTV_MANAGER', N'QLTV_STAFF')
ORDER BY role_principal.[name], member_principal.[name];
GO

/* E. Current authenticated identity. Run this while connected as each account. */
SELECT
    ORIGINAL_LOGIN() AS [original_server_login],
    SUSER_SNAME() AS [current_server_login],
    USER_NAME() AS [current_database_user];
GO

/* F. Current user's non-public application role memberships. */
SELECT role_principal.[name] AS [database_role]
FROM sys.database_role_members AS membership
INNER JOIN sys.database_principals AS role_principal
    ON role_principal.[principal_id] = membership.[role_principal_id]
INNER JOIN sys.database_principals AS member_principal
    ON member_principal.[principal_id] = membership.[member_principal_id]
WHERE member_principal.[principal_id] = USER_ID()
  AND role_principal.[name] <> N'public'
  AND role_principal.[is_fixed_role] = 0
ORDER BY role_principal.[name];
GO

/* G. Current user's effective database permissions. */
SELECT
    [entity_name],
    [subentity_name],
    [permission_name]
FROM fn_my_permissions(NULL, N'DATABASE')
ORDER BY [permission_name], [entity_name];
GO

/* H. Permission checks used for the manual comparison. */
SELECT
    HAS_PERMS_BY_NAME(N'dbo.NHANVIEN', N'OBJECT', N'SELECT')
        AS [can_select_nhanvien],
    HAS_PERMS_BY_NAME(N'dbo.ISBN', N'OBJECT', N'SELECT')
        AS [can_select_isbn];
GO

/*
    Manual SSMS test
    ----------------
    1. Open a new Database Engine connection using SQL Server Authentication.
       Login with Account A: nguyen_trong_hoang and its replacement password.
    2. Open a query in QLTV and run sections E through H.
       Expected: login nguyen_trong_hoang, database user 1,
       role QLTV_MANAGER, NHANVIEN SELECT = 1,
       and ISBN SELECT = 1.
    3. Disconnect Account A completely.
    4. Open another Database Engine connection using Account B:
       tran_thi_mai and its replacement password.
    5. Open a query in QLTV and run sections E through H.
       Expected: login tran_thi_mai, database user 2, role QLTV_STAFF,
       NHANVIEN SELECT = 1,
       and ISBN SELECT = 0 unless another existing grant supplies that access.
    6. Optional proof using SELECT statements:
           SELECT TOP (1) MANV, HONV, TENNV FROM dbo.NHANVIEN;
       should succeed for both accounts. The following should succeed for
       Account A and fail for Account B when no broader pre-existing grant exists:
           SELECT TOP (1) ISBN, TENSACH FROM dbo.ISBN;
*/
