/*
    Library Management System - application login and permissions

    This script must be executed by sqlcmd with these variables:
      APP_DB_USER
      APP_DB_PASSWORD

    Docker supplies both shared development values from .env or the Compose
    defaults. The application account receives data access only; it cannot
    create objects, administer logins, back up, restore, or control the database.
*/

:on error exit

USE [master];
GO

IF DB_ID(N'LibraryManagement') IS NULL
BEGIN
    ;THROW 50001, 'LibraryManagement does not exist. Run 01_create_tables.sql first.', 1;
END;

DECLARE @LoginName SYSNAME = N'$(APP_DB_USER)';
DECLARE @LoginPassword NVARCHAR(128) = N'$(APP_DB_PASSWORD)';
DECLARE @Command NVARCHAR(MAX);

IF NULLIF(LTRIM(RTRIM(@LoginName)), N'') IS NULL
BEGIN
    ;THROW 50002, 'APP_DB_USER must not be empty.', 1;
END;

IF LEN(@LoginPassword) < 8
BEGIN
    ;THROW 50003, 'APP_DB_PASSWORD must contain at least 8 characters.', 1;
END;

IF EXISTS
(
    SELECT 1
    FROM sys.server_principals
    WHERE name = @LoginName AND type <> 'S'
)
BEGIN
    ;THROW 50004, 'APP_DB_USER already exists but is not a SQL login.', 1;
END;

IF SUSER_ID(@LoginName) IS NULL
BEGIN
    SET @Command =
        N'CREATE LOGIN ' + QUOTENAME(@LoginName)
        + N' WITH PASSWORD = N' + QUOTENAME(@LoginPassword, '''')
        + N', CHECK_POLICY = ON, CHECK_EXPIRATION = OFF,'
        + N' DEFAULT_DATABASE = [LibraryManagement];';
END;
ELSE
BEGIN
    SET @Command =
        N'ALTER LOGIN ' + QUOTENAME(@LoginName)
        + N' WITH PASSWORD = N' + QUOTENAME(@LoginPassword, '''')
        + N', CHECK_POLICY = ON, CHECK_EXPIRATION = OFF,'
        + N' DEFAULT_DATABASE = [LibraryManagement];';
END;

EXEC sys.sp_executesql @Command;
GO

USE [LibraryManagement];
GO

DECLARE @LoginName SYSNAME = N'$(APP_DB_USER)';
DECLARE @Command NVARCHAR(MAX);

IF DATABASE_PRINCIPAL_ID(@LoginName) IS NULL
BEGIN
    SET @Command =
        N'CREATE USER ' + QUOTENAME(@LoginName)
        + N' FOR LOGIN ' + QUOTENAME(@LoginName) + N';';
END;
ELSE
BEGIN
    SET @Command =
        N'ALTER USER ' + QUOTENAME(@LoginName)
        + N' WITH LOGIN = ' + QUOTENAME(@LoginName) + N';';
END;

EXEC sys.sp_executesql @Command;

IF DATABASE_PRINCIPAL_ID(N'library_app_role') IS NULL
BEGIN
    CREATE ROLE [library_app_role] AUTHORIZATION [dbo];
END;

GRANT CONNECT TO [library_app_role];
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::[dbo] TO [library_app_role];

IF NOT EXISTS
(
    SELECT 1
    FROM sys.database_role_members AS membership
    INNER JOIN sys.database_principals AS role_principal
        ON role_principal.principal_id = membership.role_principal_id
    INNER JOIN sys.database_principals AS member_principal
        ON member_principal.principal_id = membership.member_principal_id
    WHERE role_principal.name = N'library_app_role'
      AND member_principal.name = @LoginName
)
BEGIN
    SET @Command =
        N'ALTER ROLE [library_app_role] ADD MEMBER '
        + QUOTENAME(@LoginName) + N';';
    EXEC sys.sp_executesql @Command;
END;

SELECT
    member_principal.name AS database_user,
    role_principal.name AS database_role
FROM sys.database_role_members AS membership
INNER JOIN sys.database_principals AS role_principal
    ON role_principal.principal_id = membership.role_principal_id
INNER JOIN sys.database_principals AS member_principal
    ON member_principal.principal_id = membership.member_principal_id
WHERE role_principal.name = N'library_app_role'
  AND member_principal.name = @LoginName;
GO

/* ============================================================
   Teacher's Security & Roles Requirements:
   - Server Logins: admin, nv_mai, nv_nam, docgia (Password: 123456)
   - Database Roles: QUANLY, THUTHU, DOCGIA
   - Database Users: [1], [2], [3], [4]
   - Stored Procedure: dbo.sp_LayThongTinNhanVien
   ============================================================ */

USE [master];
GO

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'admin')
    CREATE LOGIN [admin] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [admin] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_mai')
    CREATE LOGIN [nv_mai] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [nv_mai] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_nam')
    CREATE LOGIN [nv_nam] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [nv_nam] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'docgia')
    CREATE LOGIN [docgia] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [docgia] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];
GO

USE [LibraryManagement];
GO

-- 1. Create Roles
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'QUANLY' AND type = 'R')
    CREATE ROLE QUANLY;

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'THUTHU' AND type = 'R')
    CREATE ROLE THUTHU;

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'DOCGIA' AND type = 'R')
    CREATE ROLE DOCGIA;
GO

-- 2. Permissions
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO QUANLY;

GRANT SELECT, INSERT, UPDATE ON dbo.DOCGIA TO THUTHU;
GRANT SELECT, INSERT, UPDATE ON dbo.PHIEUMUON TO THUTHU;
GRANT SELECT, INSERT, UPDATE ON dbo.CT_PHIEUMUON TO THUTHU;
GRANT SELECT, UPDATE ON dbo.SACH TO THUTHU;
GRANT SELECT ON dbo.ISBN TO THUTHU;
GRANT SELECT ON dbo.THELOAI TO THUTHU;
GRANT SELECT ON dbo.TACGIA TO THUTHU;
GRANT SELECT ON dbo.TACGIA_SACH TO THUTHU;
GRANT SELECT ON dbo.NGANTU TO THUTHU;
GRANT SELECT ON dbo.NGONNGU TO THUTHU;
GRANT SELECT ON dbo.NHANVIEN TO THUTHU;
GRANT SELECT ON dbo.v_ChiTietPhieuMuon_Phat TO THUTHU;

GRANT SELECT ON dbo.ISBN TO DOCGIA;
GRANT SELECT ON dbo.SACH TO DOCGIA;
GRANT SELECT ON dbo.THELOAI TO DOCGIA;
GRANT SELECT ON dbo.TACGIA TO DOCGIA;
GRANT SELECT ON dbo.TACGIA_SACH TO DOCGIA;
GRANT SELECT ON dbo.NGANTU TO DOCGIA;
GRANT SELECT ON dbo.NGONNGU TO DOCGIA;
GO

-- 3. Map Users [1], [2], [3], [4]
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'admin' AND type = 'S')
    DROP USER [admin];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'nv_mai' AND type = 'S')
    DROP USER [nv_mai];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'nv_nam' AND type = 'S')
    DROP USER [nv_nam];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'user_docgia' AND type = 'S')
BEGIN
    ALTER ROLE [DOCGIA] DROP MEMBER [user_docgia];
    DROP USER [user_docgia];
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '1' AND type = 'S')
    CREATE USER [1] FOR LOGIN [nv_nam];
ALTER ROLE [THUTHU] ADD MEMBER [1];

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '2' AND type = 'S')
    CREATE USER [2] FOR LOGIN [nv_mai];
ALTER ROLE [THUTHU] ADD MEMBER [2];

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '3' AND type = 'S')
    CREATE USER [3] FOR LOGIN [admin];
ALTER ROLE [QUANLY] ADD MEMBER [3];

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '4' AND type = 'S')
    CREATE USER [4] FOR LOGIN [docgia];
ALTER ROLE [DOCGIA] ADD MEMBER [4];
GO

-- 4. Stored Procedures
CREATE OR ALTER PROCEDURE dbo.sp_LayThongTinNhanVien
    @LoginName NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @DBUserName NVARCHAR(100);
    DECLARE @RoleName NVARCHAR(50) = NULL;

    SELECT TOP 1 
        @DBUserName = dp.name
    FROM sys.database_principals dp
    WHERE dp.sid = SUSER_SID(@LoginName);

    IF @DBUserName IS NULL
    BEGIN
        SELECT TOP 1 @DBUserName = name 
        FROM sys.database_principals 
        WHERE name = @LoginName;
    END;

    SELECT TOP 1 @RoleName = r.name
    FROM sys.database_role_members rm
    INNER JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
    INNER JOIN sys.database_principals u ON rm.member_principal_id = u.principal_id
    WHERE u.name = @DBUserName
    ORDER BY CASE 
        WHEN r.name = 'QUANLY' THEN 1 
        WHEN r.name = 'THUTHU' THEN 2 
        WHEN r.name = 'DOCGIA' THEN 3 
        ELSE 4 END;

    IF @RoleName = 'DOCGIA' OR @LoginName = 'docgia' OR @DBUserName = 'user_docgia' OR @DBUserName = '4'
    BEGIN
        SELECT 
            @LoginName AS LoginName,
            ISNULL(@DBUserName, N'4') AS UserName,
            N'DOCGIA' AS RoleName,
            0 AS MANV,
            N'Độc Giả (Sinh Viên)' AS HoTen,
            N'docgia@qltv.edu.vn' AS Email,
            N'Độc giả' AS VaiTro;
        RETURN;
    END;

    DECLARE @MANV INT = TRY_CAST(@DBUserName AS INT);

    IF @MANV IS NULL
    BEGIN
        SELECT TOP 1 @MANV = MANV FROM dbo.NHANVIEN WHERE EMAIL LIKE @LoginName + '%';
        IF @MANV IS NULL SET @MANV = 1;
    END;

    SELECT 
        @LoginName AS LoginName,
        @DBUserName AS UserName,
        ISNULL(@RoleName, N'THUTHU') AS RoleName,
        nv.MANV,
        RTRIM(nv.HONV) + ' ' + RTRIM(nv.TENNV) AS HoTen,
        ISNULL(nv.EMAIL, 'N/A') AS Email,
        CASE 
            WHEN @RoleName = 'QUANLY' THEN N'Quản lý' 
            WHEN @RoleName = 'DOCGIA' THEN N'Độc giả'
            ELSE N'Thủ thư' 
        END AS VaiTro
    FROM dbo.NHANVIEN nv
    WHERE nv.MANV = @MANV;
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_LayThongTinHienTai
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @CurrentLogin NVARCHAR(100) = SUSER_SNAME();
    EXEC dbo.sp_LayThongTinNhanVien @LoginName = @CurrentLogin;
END;
GO

GRANT EXECUTE ON dbo.sp_LayThongTinNhanVien TO QUANLY, THUTHU, DOCGIA;
GRANT EXECUTE ON dbo.sp_LayThongTinHienTai TO QUANLY, THUTHU, DOCGIA;
GO
