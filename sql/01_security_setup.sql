/*
    Library Management security demo - database roles and permissions only

    Review this file before running it manually in SSMS.
    This script does not create logins or users and does not change tables.

    If your database is not named QLTV, replace [QLTV] below.
*/

USE [QLTV];
GO

/* 1. Create the application database roles if they do not already exist. */
IF DATABASE_PRINCIPAL_ID(N'QLTV_MANAGER') IS NULL
BEGIN
    CREATE ROLE [QLTV_MANAGER] AUTHORIZATION [dbo];
END;
GO

IF DATABASE_PRINCIPAL_ID(N'QLTV_STAFF') IS NULL
BEGIN
    CREATE ROLE [QLTV_STAFF] AUTHORIZATION [dbo];
END;
GO

/*
    2. Grant only the permissions needed for this security demonstration.

    Both roles need to connect and read NHANVIEN so the Python application can
    map the authenticated SQL login name to MANV and display HONV + TENNV.
*/
GRANT CONNECT TO [QLTV_MANAGER];
GRANT CONNECT TO [QLTV_STAFF];

GRANT SELECT ON OBJECT::[dbo].[NHANVIEN] TO [QLTV_MANAGER];
GRANT SELECT ON OBJECT::[dbo].[NHANVIEN] TO [QLTV_STAFF];
GO

/*
    3. Give the manager a visibly broader read-only permission for the demo.

    QLTV_MANAGER can read all current and future tables/views in dbo.
    QLTV_STAFF receives no schema-wide permission here and can only read
    NHANVIEN through this script.
*/
GRANT SELECT ON SCHEMA::[dbo] TO [QLTV_MANAGER];
GO

/* No INSERT, UPDATE, DELETE, EXECUTE, CONTROL, or server role is granted. */

