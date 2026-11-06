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
   - Server Logins belong only to valid NHANVIEN rows.
   - Database Roles: QUANLY, THUTHU
   - Database Users: [1], [2], [3], [4]
   - Stored Procedure: dbo.sp_LayThongTinNhanVien
   ============================================================ */

USE [master];
GO

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'admin')
    CREATE LOGIN [admin] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [admin] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_huong')
    CREATE LOGIN [nv_huong] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [nv_huong] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_long')
    CREATE LOGIN [nv_long] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [nv_long] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_nam')
    CREATE LOGIN [nv_nam] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF, DEFAULT_DATABASE = [LibraryManagement];
ELSE
    ALTER LOGIN [nv_nam] WITH PASSWORD = '123456', DEFAULT_DATABASE = [LibraryManagement];

GO

USE [LibraryManagement];
GO

-- 1. Create Roles
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'QUANLY' AND type = 'R')
    CREATE ROLE QUANLY;

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'THUTHU' AND type = 'R')
    CREATE ROLE THUTHU;

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

GO

-- 3. Map one employee login to each valid NHANVIEN ID.
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'admin' AND type = 'S')
    DROP USER [admin];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'nv_mai' AND type = 'S')
    DROP USER [nv_mai];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'nv_nam' AND type = 'S')
    DROP USER [nv_nam];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'user_docgia' AND type = 'S')
BEGIN
    IF DATABASE_PRINCIPAL_ID(N'DOCGIA') IS NOT NULL
        ALTER ROLE [DOCGIA] DROP MEMBER [user_docgia];
    DROP USER [user_docgia];
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '1' AND type = 'S')
    CREATE USER [1] FOR LOGIN [nv_huong];
ELSE
    ALTER USER [1] WITH LOGIN = [nv_huong];
IF NOT EXISTS (
    SELECT 1 FROM sys.database_role_members rm
    JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
    JOIN sys.database_principals u ON u.principal_id = rm.member_principal_id
    WHERE r.name = 'THUTHU' AND u.name = '1'
)
    ALTER ROLE [THUTHU] ADD MEMBER [1];

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '2' AND type = 'S')
    CREATE USER [2] FOR LOGIN [nv_long];
ELSE
    ALTER USER [2] WITH LOGIN = [nv_long];
IF NOT EXISTS (
    SELECT 1 FROM sys.database_role_members rm
    JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
    JOIN sys.database_principals u ON u.principal_id = rm.member_principal_id
    WHERE r.name = 'THUTHU' AND u.name = '2'
)
    ALTER ROLE [THUTHU] ADD MEMBER [2];

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '3' AND type = 'S')
    CREATE USER [3] FOR LOGIN [admin];
ELSE
    ALTER USER [3] WITH LOGIN = [admin];
IF NOT EXISTS (
    SELECT 1 FROM sys.database_role_members rm
    JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
    JOIN sys.database_principals u ON u.principal_id = rm.member_principal_id
    WHERE r.name = 'QUANLY' AND u.name = '3'
)
    ALTER ROLE [QUANLY] ADD MEMBER [3];

IF DATABASE_PRINCIPAL_ID(N'DOCGIA') IS NOT NULL AND EXISTS (
    SELECT 1 FROM sys.database_role_members rm
    JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
    JOIN sys.database_principals u ON u.principal_id = rm.member_principal_id
    WHERE r.name = 'DOCGIA' AND u.name = '4'
)
    ALTER ROLE [DOCGIA] DROP MEMBER [4];

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '4' AND type = 'S')
    CREATE USER [4] FOR LOGIN [nv_nam];
ELSE
    ALTER USER [4] WITH LOGIN = [nv_nam];
IF NOT EXISTS (
    SELECT 1 FROM sys.database_role_members rm
    JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
    JOIN sys.database_principals u ON u.principal_id = rm.member_principal_id
    WHERE r.name = 'THUTHU' AND u.name = '4'
)
    ALTER ROLE [THUTHU] ADD MEMBER [4];
GO

USE [master];
GO
IF SUSER_ID(N'nv_mai') IS NOT NULL DROP LOGIN [nv_mai];
IF SUSER_ID(N'docgia') IS NOT NULL DROP LOGIN [docgia];
GO

USE [LibraryManagement];
GO
IF DATABASE_PRINCIPAL_ID(N'DOCGIA') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.database_role_members
       WHERE role_principal_id = DATABASE_PRINCIPAL_ID(N'DOCGIA')
   )
    DROP ROLE [DOCGIA];
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
        ELSE 3 END;

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

GRANT EXECUTE ON dbo.sp_LayThongTinNhanVien TO QUANLY, THUTHU;
GRANT EXECUTE ON dbo.sp_LayThongTinHienTai TO QUANLY, THUTHU;
GO

/* ============================================================
   Account administration required by the classroom assignment.
   A valid employee account is identified by database user = MANV.
   ============================================================ */

CREATE OR ALTER PROCEDURE dbo.sp_DanhSachTaiKhoanNhanVien
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        nv.MANV,
        CONCAT(RTRIM(nv.HONV), N' ', RTRIM(nv.TENNV)) AS HOTEN,
        nv.EMAIL,
        CAST(CASE WHEN dp.principal_id IS NULL THEN 0 ELSE 1 END AS BIT) AS DaCoTaiKhoan,
        SUSER_SNAME(dp.sid) AS LoginName,
        app_role.RoleName
    FROM dbo.NHANVIEN AS nv
    LEFT JOIN sys.database_principals AS dp
      ON dp.name = CONVERT(NVARCHAR(20), nv.MANV)
     AND dp.type = 'S'
    /* One row per employee: users may also belong to other roles
       (e.g. db_backupoperator from 04_backup_and_restore.sql). */
    OUTER APPLY
    (
        SELECT TOP (1) role_dp.name AS RoleName
        FROM sys.database_role_members AS drm
        INNER JOIN sys.database_principals AS role_dp
            ON role_dp.principal_id = drm.role_principal_id
        WHERE drm.member_principal_id = dp.principal_id
          AND role_dp.name IN (N'QUANLY', N'THUTHU')
        ORDER BY CASE role_dp.name WHEN N'QUANLY' THEN 0 ELSE 1 END
    ) AS app_role
    WHERE nv.MANV > 0
    ORDER BY nv.MANV;
END;
GO

GRANT EXECUTE ON dbo.sp_DanhSachTaiKhoanNhanVien TO QUANLY;
GO

USE [LibraryManagement];
GO

/* Certificate signing gives only these procedures ALTER LOGIN / ALTER USER.
   The manager login itself receives no broad server-level permission. */
IF CERT_ID(N'QLTV_AccountAdminCertificate') IS NULL
    CREATE CERTIFICATE QLTV_AccountAdminCertificate
        ENCRYPTION BY PASSWORD = 'QLTV-Cert-2026!'
        WITH SUBJECT = 'Limited account administration for QLTV';
GO

IF NOT EXISTS (SELECT 1 FROM master.sys.certificates WHERE name = N'QLTV_AccountAdminCertificate')
    BACKUP CERTIFICATE QLTV_AccountAdminCertificate
        TO FILE = '/var/opt/mssql/data/QLTV_AccountAdminCertificate.cer';
GO

USE [master];
GO
IF CERT_ID(N'QLTV_AccountAdminCertificate') IS NULL
    CREATE CERTIFICATE QLTV_AccountAdminCertificate
        FROM FILE = '/var/opt/mssql/data/QLTV_AccountAdminCertificate.cer';
IF SUSER_ID(N'QLTV_AccountAdminCertificateLogin') IS NULL
    CREATE LOGIN QLTV_AccountAdminCertificateLogin
        FROM CERTIFICATE QLTV_AccountAdminCertificate;
GRANT ALTER ANY LOGIN TO QLTV_AccountAdminCertificateLogin;
DROP PROCEDURE IF EXISTS dbo.sp_QLTV_TaoTaiKhoanNhanVien;
DROP PROCEDURE IF EXISTS dbo.sp_QLTV_XoaTaiKhoanNhanVien;
GO

USE [LibraryManagement];
GO
IF USER_ID(N'QLTV_AccountAdminCertificateUser') IS NULL
    CREATE USER QLTV_AccountAdminCertificateUser
        FROM CERTIFICATE QLTV_AccountAdminCertificate;
GRANT ALTER ANY USER TO QLTV_AccountAdminCertificateUser;
GRANT ALTER ON ROLE::THUTHU TO QLTV_AccountAdminCertificateUser;
GRANT ALTER ON ROLE::QUANLY TO QLTV_AccountAdminCertificateUser;
GO

CREATE OR ALTER PROCEDURE dbo.sp_TaoTaiKhoanNhanVien
    @MANV INT,
    @LoginName SYSNAME,
    @Password NVARCHAR(128),
    @RoleName SYSNAME = N'THUTHU'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @LoginName = NULLIF(LTRIM(RTRIM(@LoginName)), N'');
    SET @RoleName = UPPER(NULLIF(LTRIM(RTRIM(@RoleName)), N''));

    IF @MANV <= 0 OR NOT EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE MANV = @MANV)
        THROW 51001, N'Mã nhân viên không hợp lệ.', 1;
    IF @LoginName IS NULL
        THROW 51002, N'Tên đăng nhập không được để trống.', 1;
    IF LEN(@Password) < 6
        THROW 51003, N'Mật khẩu phải có ít nhất 6 ký tự.', 1;
    IF @RoleName NOT IN (N'QUANLY', N'THUTHU')
        THROW 51004, N'Nhóm quyền chỉ có thể là QUANLY hoặc THUTHU.', 1;
    IF EXISTS (
        SELECT 1 FROM sys.database_principals
        WHERE name = CONVERT(NVARCHAR(20), @MANV)
    )
        THROW 51005, N'Nhân viên này đã có tài khoản.', 1;
    IF SUSER_ID(@LoginName) IS NOT NULL
        THROW 51006, N'Tên đăng nhập đã tồn tại trên SQL Server.', 1;

    DECLARE @Sql NVARCHAR(MAX);
    DECLARE @DatabaseUser SYSNAME = CONVERT(NVARCHAR(20), @MANV);

    BEGIN TRY
        BEGIN TRANSACTION;
        SET @Sql = N'CREATE LOGIN ' + QUOTENAME(@LoginName)
                 + N' WITH PASSWORD = N' + QUOTENAME(@Password, '''')
                 + N', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF,'
                 + N' DEFAULT_DATABASE = [LibraryManagement];';
        EXEC sys.sp_executesql @Sql;

        SET @Sql = N'CREATE USER ' + QUOTENAME(@DatabaseUser)
                 + N' FOR LOGIN ' + QUOTENAME(@LoginName) + N';'
                 + N' ALTER ROLE ' + QUOTENAME(@RoleName)
                 + N' ADD MEMBER ' + QUOTENAME(@DatabaseUser) + N';';
        EXEC sys.sp_executesql @Sql;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_TaoNhanVienVaTaiKhoan
    @HONV NVARCHAR(50),
    @TENNV NVARCHAR(12),
    @GIOITINH BIT,
    @DIACHI NVARCHAR(100) = NULL,
    @DIENTHOAI VARCHAR(11) = NULL,
    @EMAIL VARCHAR(50) = NULL,
    @LoginName SYSNAME,
    @Password NVARCHAR(128),
    @RoleName SYSNAME = N'THUTHU'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @HONV = NULLIF(LTRIM(RTRIM(@HONV)), N'');
    SET @TENNV = NULLIF(LTRIM(RTRIM(@TENNV)), N'');
    SET @DIACHI = NULLIF(LTRIM(RTRIM(@DIACHI)), N'');
    SET @DIENTHOAI = NULLIF(LTRIM(RTRIM(@DIENTHOAI)), '');
    SET @EMAIL = NULLIF(LOWER(LTRIM(RTRIM(@EMAIL))), '');

    IF @HONV IS NULL OR @TENNV IS NULL
        THROW 51021, N'Họ và tên nhân viên không được để trống.', 1;
    IF @EMAIL IS NOT NULL AND EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE EMAIL = @EMAIL)
        THROW 51022, N'Email nhân viên đã tồn tại.', 1;
    IF @DIENTHOAI IS NOT NULL AND EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE DIENTHOAI = @DIENTHOAI)
        THROW 51023, N'Số điện thoại nhân viên đã tồn tại.', 1;

    DECLARE @NewMANV INT;
    BEGIN TRY
        BEGIN TRANSACTION;
        INSERT INTO dbo.NHANVIEN
            (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL)
        VALUES
            (@HONV, @TENNV, @GIOITINH, @DIACHI, @DIENTHOAI, @EMAIL);

        SET @NewMANV = CONVERT(INT, SCOPE_IDENTITY());
        EXEC dbo.sp_TaoTaiKhoanNhanVien
            @MANV = @NewMANV,
            @LoginName = @LoginName,
            @Password = @Password,
            @RoleName = @RoleName;
        COMMIT TRANSACTION;

        SELECT @NewMANV AS MANV;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_XoaTaiKhoanNhanVien
    @MANV INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @MANV <= 0 OR NOT EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE MANV = @MANV)
        THROW 51011, N'Mã nhân viên không hợp lệ.', 1;

    DECLARE @DatabaseUser SYSNAME = CONVERT(NVARCHAR(20), @MANV);
    DECLARE @LoginName SYSNAME;
    DECLARE @RoleName SYSNAME;
    DECLARE @Sql NVARCHAR(MAX);

    SELECT @LoginName = SUSER_SNAME(sid)
    FROM sys.database_principals
    WHERE name = @DatabaseUser AND type = 'S';

    IF @LoginName IS NULL
        THROW 51012, N'Nhân viên này chưa có tài khoản.', 1;
    IF @LoginName = ORIGINAL_LOGIN()
        THROW 51013, N'Không thể xóa chính tài khoản đang đăng nhập.', 1;

    SELECT TOP (1) @RoleName = role_dp.name
    FROM sys.database_role_members AS drm
    JOIN sys.database_principals AS member_dp
      ON member_dp.principal_id = drm.member_principal_id
    JOIN sys.database_principals AS role_dp
      ON role_dp.principal_id = drm.role_principal_id
    WHERE member_dp.name = @DatabaseUser
      AND role_dp.name IN (N'QUANLY', N'THUTHU');

    BEGIN TRY
        BEGIN TRANSACTION;
        IF @RoleName IS NOT NULL
        BEGIN
            SET @Sql = N'ALTER ROLE ' + QUOTENAME(@RoleName)
                     + N' DROP MEMBER ' + QUOTENAME(@DatabaseUser) + N';';
            EXEC sys.sp_executesql @Sql;
        END;
        SET @Sql = N'DROP USER ' + QUOTENAME(@DatabaseUser) + N';';
        EXEC sys.sp_executesql @Sql;
        SET @Sql = N'DROP LOGIN ' + QUOTENAME(@LoginName) + N';';
        EXEC sys.sp_executesql @Sql;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        DECLARE @DeleteErrorNumber INT = ERROR_NUMBER();
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF @DeleteErrorNumber = 15434
            THROW 51014, N'Tài khoản đang được sử dụng. Hãy đăng xuất tài khoản đó rồi thử lại.', 1;
        THROW;
    END CATCH;
END;
GO

IF EXISTS (
    SELECT 1 FROM sys.crypt_properties
    WHERE major_id = OBJECT_ID(N'dbo.sp_TaoTaiKhoanNhanVien')
)
    DROP SIGNATURE FROM OBJECT::dbo.sp_TaoTaiKhoanNhanVien
        BY CERTIFICATE QLTV_AccountAdminCertificate;
ADD SIGNATURE TO OBJECT::dbo.sp_TaoTaiKhoanNhanVien
    BY CERTIFICATE QLTV_AccountAdminCertificate
    WITH PASSWORD = 'QLTV-Cert-2026!';

IF EXISTS (
    SELECT 1 FROM sys.crypt_properties
    WHERE major_id = OBJECT_ID(N'dbo.sp_XoaTaiKhoanNhanVien')
)
    DROP SIGNATURE FROM OBJECT::dbo.sp_XoaTaiKhoanNhanVien
        BY CERTIFICATE QLTV_AccountAdminCertificate;
ADD SIGNATURE TO OBJECT::dbo.sp_XoaTaiKhoanNhanVien
    BY CERTIFICATE QLTV_AccountAdminCertificate
    WITH PASSWORD = 'QLTV-Cert-2026!';

GRANT EXECUTE ON dbo.sp_TaoTaiKhoanNhanVien TO QUANLY;
GRANT EXECUTE ON dbo.sp_TaoNhanVienVaTaiKhoan TO QUANLY;
GRANT EXECUTE ON dbo.sp_XoaTaiKhoanNhanVien TO QUANLY;
GO
