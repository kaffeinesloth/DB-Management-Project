/* ============================================================
   SCRIPT THIẾT LẬP BẢO MẬT & PHÂN QUYỀN CHUẨN SQL SERVER (QLTV)
   Chuẩn hóa theo đúng yêu cầu môn Hệ Quản Trị Cơ Sở Dữ Liệu:
   1. Tạo Database Roles: QUANLY và THUTHU trong QLTV.
   2. Phân quyền chi tiết trên từng bảng/thao tác cho các Roles.
   3. Tạo Server Logins (cấp Server) & Database Users (cấp Database).
   4. Thêm User vào các Role tương ứng.
   5. Thêm Stored Procedure truy vấn tự động: SUSER_SNAME(), USER_NAME(), ROLENAME, MANV.
   ============================================================ */

USE QLTV;
GO

-- 1. TẠO CÁC DATABASE ROLES TRONG DATABASE QLTV
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'QUANLY' AND type = 'R')
BEGIN
    CREATE ROLE QUANLY;
END;
GO

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'THUTHU' AND type = 'R')
BEGIN
    CREATE ROLE THUTHU;
END;
GO

-- 2. PHÂN QUYỀN CHO DATABASE ROLES
-- Role QUANLY: Toàn quyền quản trị dữ liệu trong schema dbo
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO QUANLY;

-- Role THUTHU: Quyền nghiệp vụ thư viện thường ngày
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.DOCGIA TO THUTHU;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.PHIEUMUON TO THUTHU;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.CT_PHIEUMUON TO THUTHU;
GRANT SELECT, UPDATE ON dbo.SACH TO THUTHU;
GRANT SELECT ON dbo.ISBN TO THUTHU;
GRANT SELECT ON dbo.THELOAI TO THUTHU;
GRANT SELECT ON dbo.TACGIA TO THUTHU;
GRANT SELECT ON dbo.TACGIA_SACH TO THUTHU;
GRANT SELECT ON dbo.NGANTU TO THUTHU;
GRANT SELECT ON dbo.NGONNGU TO THUTHU;
GRANT SELECT ON dbo.NHANVIEN TO THUTHU;
GO

-- 3. TẠO SERVER LOGINS (CẤP SERVER) VÀ DATABASE USERS (CẤP DATABASE)
USE master;
GO

-- 3.1. Login cho Quản lý: admin
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'admin')
BEGIN
    CREATE LOGIN [admin] WITH PASSWORD = 'Admin@123', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [admin] WITH PASSWORD = 'Admin@123';
END;
GO

-- Cấp quyền securityadmin cho login admin (để admin có thể tạo login mới theo yêu cầu note của thầy)
ALTER SERVER ROLE [securityadmin] ADD MEMBER [admin];
GO

-- 3.2. Login cho Thủ thư: nv_mai
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'nv_mai')
BEGIN
    CREATE LOGIN [nv_mai] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [nv_mai] WITH PASSWORD = '123456';
END;
GO

-- 3.3. Login cho Thủ thư: nv_nam
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'nv_nam')
BEGIN
    CREATE LOGIN [nv_nam] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [nv_nam] WITH PASSWORD = '123456';
END;
GO

-- 4. ÁNH XẠ LOGINS SANG DATABASE USERS TRONG QLTV & THÊM VÀO ROLES
USE QLTV;
GO

-- Map User [admin]
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'admin' AND type = 'S')
BEGIN
    CREATE USER [admin] FOR LOGIN [admin];
END;
ALTER ROLE [QUANLY] ADD MEMBER [admin];
GO

-- Map User [nv_mai]
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'nv_mai' AND type = 'S')
BEGIN
    CREATE USER [nv_mai] FOR LOGIN [nv_mai];
END;
ALTER ROLE [THUTHU] ADD MEMBER [nv_mai];
GO

-- Map User [nv_nam]
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'nv_nam' AND type = 'S')
BEGIN
    CREATE USER [nv_nam] FOR LOGIN [nv_nam];
END;
ALTER ROLE [THUTHU] ADD MEMBER [nv_nam];
GO

-- Đảm bảo bảng NHANVIEN có trường TENDANGNHAP để liên kết LoginName với Employee ID (MANV)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.NHANVIEN') AND name = 'TENDANGNHAP')
BEGIN
    ALTER TABLE dbo.NHANVIEN ADD TENDANGNHAP VARCHAR(50) NULL;
END;
GO

UPDATE dbo.NHANVIEN SET TENDANGNHAP = 'admin' WHERE MANV = 1;
UPDATE dbo.NHANVIEN SET TENDANGNHAP = 'nv_mai' WHERE MANV = 2;
UPDATE dbo.NHANVIEN SET TENDANGNHAP = 'nv_nam' WHERE MANV = 3;
GO

-- 5. STORED PROCEDURES CHO HỆ THỐNG ĐĂNG NHẬP THEO CHUẨN BẢO MẬT

-- 5.1. Tra cứu nhanh thông tin nhân viên theo Login Name (để auto hiện Employee ID khi gõ username)
CREATE OR ALTER PROCEDURE dbo.sp_TraCuuNhanVienTheoLogin
    @LoginName VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT 
        nv.MANV,
        RTRIM(nv.HONV) + ' ' + RTRIM(nv.TENNV) AS HoTen,
        nv.EMAIL,
        nv.TENDANGNHAP,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM sys.database_role_members rm
                JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.database_principals u ON rm.member_principal_id = u.principal_id
                WHERE u.name = @LoginName AND r.name = 'QUANLY'
            ) THEN 'QUANLY'
            ELSE 'THUTHU'
        END AS RoleName
    FROM dbo.NHANVIEN nv
    WHERE nv.TENDANGNHAP = @LoginName;
END;
GO

-- 5.2. Lấy thông tin định danh của người dùng hiện tại đang kết nối phiên làm việc
CREATE OR ALTER PROCEDURE dbo.sp_LayThongTinHienTai
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CurrentLogin NVARCHAR(100) = SUSER_SNAME();
    DECLARE @CurrentDBUser NVARCHAR(100) = USER_NAME();
    DECLARE @Role NVARCHAR(50) = N'THUTHU';

    IF IS_ROLEMEMBER('QUANLY') = 1 OR IS_SRVROLEMEMBER('sysadmin') = 1
        SET @Role = N'QUANLY';
    ELSE IF IS_ROLEMEMBER('THUTHU') = 1
        SET @Role = N'THUTHU';

    SELECT 
        @CurrentLogin AS LoginName,
        @CurrentDBUser AS UserName,
        @Role AS RoleName,
        ISNULL(nv.MANV, 0) AS MANV,
        ISNULL(RTRIM(nv.HONV) + ' ' + RTRIM(nv.TENNV), @CurrentLogin) AS HoTen,
        ISNULL(nv.EMAIL, 'N/A') AS Email
    FROM (SELECT 1 AS dummy) d
    LEFT JOIN dbo.NHANVIEN nv ON nv.TENDANGNHAP = @CurrentLogin;
END;
GO

-- Cấp quyền EXECUTE 2 Stored Procedures này cho cả 2 roles
GRANT EXECUTE ON dbo.sp_TraCuuNhanVienTheoLogin TO QUANLY, THUTHU;
GRANT EXECUTE ON dbo.sp_LayThongTinHienTai TO QUANLY, THUTHU;
GO
