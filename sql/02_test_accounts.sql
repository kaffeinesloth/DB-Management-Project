/*
    Library Management security demo - two example SQL Server accounts

    IMPORTANT BEFORE RUNNING MANUALLY IN SSMS:
    1. Replace both placeholder passwords.
    2. Confirm that QLTV.dbo.NHANVIEN contains MANV 1 and MANV 2.
    3. If you use different employee IDs, replace database users [1] and [2].
       You may also replace the readable server login names independently.
    4. Run sql/01_security_setup.sql first.

    Each readable server login maps to a numeric database user equal to MANV.
*/

/* Stop before creating anything when the employee mappings are not valid. */
USE [QLTV];
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[NHANVIEN] WHERE [MANV] = 1)
BEGIN
    THROW 51001, 'MANV 1 does not exist in QLTV.dbo.NHANVIEN.', 1;
END;

IF NOT EXISTS (SELECT 1 FROM [dbo].[NHANVIEN] WHERE [MANV] = 2)
BEGIN
    THROW 51002, 'MANV 2 does not exist in QLTV.dbo.NHANVIEN.', 1;
END;
GO

/* 1. Create the server-level SQL logins. Existing logins are left unchanged. */
USE [master];
GO

IF SUSER_ID(N'nguyen_trong_hoang') IS NULL
BEGIN
    /* Replace CHANGE_ME_Test1! before execution. */
    CREATE LOGIN [nguyen_trong_hoang]
        WITH PASSWORD = 'CHANGE_ME_Test1!',
             CHECK_POLICY = ON,
             CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    PRINT 'Login [nguyen_trong_hoang] already exists; password was not changed.';
END;
GO

IF SUSER_ID(N'tran_thi_mai') IS NULL
BEGIN
    /* Replace CHANGE_ME_Test2! before execution. */
    CREATE LOGIN [tran_thi_mai]
        WITH PASSWORD = 'CHANGE_ME_Test2!',
             CHECK_POLICY = ON,
             CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    PRINT 'Login [tran_thi_mai] already exists; password was not changed.';
END;
GO

/* 2. Map each login to a database user with the same name. */
USE [QLTV];
GO

IF DATABASE_PRINCIPAL_ID(N'1') IS NULL
BEGIN
    CREATE USER [1] FOR LOGIN [nguyen_trong_hoang];
END;
GO

IF DATABASE_PRINCIPAL_ID(N'2') IS NULL
BEGIN
    CREATE USER [2] FOR LOGIN [tran_thi_mai];
END;
GO

/* 3. Add each user to one application role, with duplicate-safe guards. */
IF NOT EXISTS
(
    SELECT 1
    FROM sys.database_role_members AS membership
    WHERE membership.role_principal_id = DATABASE_PRINCIPAL_ID(N'QLTV_MANAGER')
      AND membership.member_principal_id = DATABASE_PRINCIPAL_ID(N'1')
)
BEGIN
    ALTER ROLE [QLTV_MANAGER] ADD MEMBER [1];
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.database_role_members AS membership
    WHERE membership.role_principal_id = DATABASE_PRINCIPAL_ID(N'QLTV_STAFF')
      AND membership.member_principal_id = DATABASE_PRINCIPAL_ID(N'2')
)
BEGIN
    ALTER ROLE [QLTV_STAFF] ADD MEMBER [2];
END;
GO

/* No sysadmin, securityadmin, db_owner, or other elevated role is assigned. */
