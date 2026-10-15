/* ============================================================
   SCRIPT THIẾT LẬP BẢO MẬT & PHÂN QUYỀN CHUẨN SQL SERVER (QLTV)
   Chuẩn hóa theo đúng góp ý của Giảng viên:
   - 1. Tạo 3 Database Roles: QUANLY, THUTHU và DOCGIA.
   - 2. Phân quyền chi tiết (Least Privilege):
        + QUANLY: Toàn quyền quản trị hệ thống.
        + THUTHU: Quyền nghiệp vụ phục vụ bạn đọc (không cấp DELETE chứng từ/độc giả).
        + DOCGIA: Chỉ quyền ĐỌC (SELECT) danh mục sách để sinh viên tra cứu.
   - 3. Tạo Server Logins (cấp Server): admin, nv_mai, nv_nam, docgia (Mật khẩu: 123456).
   - 4. Ánh xạ Logins sang Database Users theo Mã Nhân Viên (dạng số nguyên):
        + Login nv_nam -> Database User [1] (MANV = 1) -> Role THUTHU
        + Login nv_mai -> Database User [2] (MANV = 2) -> Role THUTHU
        + Login admin  -> Database User [3] (MANV = 3) -> Role QUANLY
        + Login docgia -> Database User [docgia]       -> Role DOCGIA
   - 5. Stored Procedure nhận tham số @LoginName, tra cứu động qua SID,
        tự động đọc Mã NV từ Database User name mà không hardcode IF...ELSE.
   ============================================================ */

USE QLTV;
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- ============================================================
-- 1. TẠO CÁC DATABASE ROLES TRONG DATABASE QLTV
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'QUANLY' AND type = 'R')
BEGIN
    CREATE ROLE QUANLY;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'THUTHU' AND type = 'R')
BEGIN
    CREATE ROLE THUTHU;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'DOCGIA' AND type = 'R')
BEGIN
    CREATE ROLE DOCGIA;
END;
GO

-- ============================================================
-- 2. PHÂN QUYỀN CHO DATABASE ROLES
-- ============================================================

-- 2.1. Role QUANLY: Toàn quyền quản trị dữ liệu trong schema dbo
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO QUANLY;

-- 2.2. Role THUTHU: Quyền nghiệp vụ phục vụ bạn đọc (Tuân thủ Least Privilege, không cấp DELETE)
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

-- 2.3. Role DOCGIA: Dành cho toàn bộ sinh viên, chỉ được phép tra cứu sách
GRANT SELECT ON dbo.ISBN TO DOCGIA;
GRANT SELECT ON dbo.SACH TO DOCGIA;
GRANT SELECT ON dbo.THELOAI TO DOCGIA;
GRANT SELECT ON dbo.TACGIA TO DOCGIA;
GRANT SELECT ON dbo.TACGIA_SACH TO DOCGIA;
GRANT SELECT ON dbo.NGANTU TO DOCGIA;
GRANT SELECT ON dbo.NGONNGU TO DOCGIA;
GO

-- ============================================================
-- 3. TẠO SERVER LOGINS (CẤP SERVER - MASTER)
-- ============================================================
USE master;
GO

-- 3.1. Login Quản lý: admin
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'admin')
BEGIN
    CREATE LOGIN [admin] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [admin] WITH PASSWORD = '123456';
END;
GO

-- 3.2. Login Thủ thư: nv_mai
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_mai')
BEGIN
    CREATE LOGIN [nv_mai] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [nv_mai] WITH PASSWORD = '123456';
END;
GO

-- 3.3. Login Thủ thư: nv_nam
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'nv_nam')
BEGIN
    CREATE LOGIN [nv_nam] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [nv_nam] WITH PASSWORD = '123456';
END;
GO

-- 3.4. Login dùng chung cho Độc giả / Sinh viên: docgia
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'docgia')
BEGIN
    CREATE LOGIN [docgia] WITH PASSWORD = '123456', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
END;
ELSE
BEGIN
    ALTER LOGIN [docgia] WITH PASSWORD = '123456';
END;
GO

-- ============================================================
-- 4. ÁNH XẠ LOGINS SANG DATABASE USERS TRONG QLTV & GÁN ROLE
-- Quy chuẩn: Database User name = Mã nhân viên (dạng số nguyên 1, 2, 3)
-- ============================================================
USE QLTV;
GO

-- Dọn dẹp tên user cũ dạng chữ (nếu từng tạo trước đây) để tránh xung đột mapping SID
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'admin' AND type = 'S')
    DROP USER [admin];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'nv_mai' AND type = 'S')
    DROP USER [nv_mai];
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'nv_nam' AND type = 'S')
    DROP USER [nv_nam];
GO

-- 4.1. Map User [1] cho Login [nv_nam] -> MANV = 1 (Thủ thư)
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '1' AND type = 'S')
BEGIN
    CREATE USER [1] FOR LOGIN [nv_nam];
END;
ALTER ROLE [THUTHU] ADD MEMBER [1];
GO

-- 4.2. Map User [2] cho Login [nv_mai] -> MANV = 2 (Thủ thư)
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '2' AND type = 'S')
BEGIN
    CREATE USER [2] FOR LOGIN [nv_mai];
END;
ALTER ROLE [THUTHU] ADD MEMBER [2];
GO

-- 4.3. Map User [3] cho Login [admin] -> MANV = 3 (Quản lý)
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '3' AND type = 'S')
BEGIN
    CREATE USER [3] FOR LOGIN [admin];
END;
ALTER ROLE [QUANLY] ADD MEMBER [3];
GO

-- 4.4. Map User [user_docgia] cho Login [docgia] -> Độc giả tra cứu (tránh trùng tên với Role DOCGIA)
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'user_docgia' AND type = 'S')
BEGIN
    CREATE USER [user_docgia] FOR LOGIN [docgia];
END;
ALTER ROLE [DOCGIA] ADD MEMBER [user_docgia];
GO

-- ============================================================
-- 5. STORED PROCEDURE ĐĂNG NHẬP & LẤY THÔNG TIN ĐỊNH DANH
-- Nhận tham số @LoginName, truy vấn động qua SID hệ thống,
-- tự động trích xuất MANV từ tên Database User mà không hardcode IF...ELSE.
-- ============================================================
CREATE OR ALTER PROCEDURE dbo.sp_LayThongTinNhanVien
    @LoginName NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. Tìm Database User tương ứng với @LoginName qua hàm chuẩn SUSER_SID()
    DECLARE @DBUserName NVARCHAR(100);
    DECLARE @RoleName NVARCHAR(50) = NULL;

    SELECT TOP 1 
        @DBUserName = dp.name
    FROM sys.database_principals dp
    WHERE dp.sid = SUSER_SID(@LoginName);

    -- Nếu không tìm thấy qua SID (phòng khi kiểm thử truyền thẳng tên Database User)
    IF @DBUserName IS NULL
    BEGIN
        SELECT TOP 1 @DBUserName = name 
        FROM sys.database_principals 
        WHERE name = @LoginName;
    END;

    -- 2. Tìm Role của User trong Database QLTV (Ưu tiên QUANLY > THUTHU > DOCGIA)
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

    -- 3. Trường hợp ĐỘC GIẢ (Sinh viên tra cứu sách)
    IF @RoleName = 'DOCGIA' OR @LoginName = 'docgia' OR @DBUserName = 'user_docgia'
    BEGIN
        SELECT 
            @LoginName AS LoginName,
            ISNULL(@DBUserName, N'user_docgia') AS UserName,
            N'DOCGIA' AS RoleName,
            0 AS MANV,
            N'Độc Giả (Sinh Viên)' AS HoTen,
            N'docgia@qltv.edu.vn' AS Email,
            N'Độc giả' AS VaiTro;
        RETURN;
    END;

    -- 4. Trường hợp NHÂN VIÊN:
    -- Lấy MANV từ chính Database User name (User name chính là MANV: 1, 2, 3...)
    DECLARE @MANV INT = TRY_CAST(@DBUserName AS INT);

    -- Dự phòng: Nếu tên User chưa đổi sang số, tìm theo Email nhân viên
    IF @MANV IS NULL
    BEGIN
        SELECT TOP 1 @MANV = MANV FROM dbo.NHANVIEN WHERE EMAIL LIKE @LoginName + '%';
        IF @MANV IS NULL SET @MANV = 1;
    END;

    -- 5. Trả về thông tin đầy đủ kết hợp từ bảng NHANVIEN
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

-- Thủ tục tương thích ngược (nếu ai đó gọi SP cũ không tham số)
CREATE OR ALTER PROCEDURE dbo.sp_LayThongTinHienTai
WITH EXECUTE AS OWNER
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @CurrentLogin NVARCHAR(100) = SUSER_SNAME();
    EXEC dbo.sp_LayThongTinNhanVien @LoginName = @CurrentLogin;
END;
GO

-- Cấp quyền thực thi Stored Procedure cho tất cả các Role
GRANT EXECUTE ON dbo.sp_LayThongTinNhanVien TO QUANLY, THUTHU, DOCGIA;
GRANT EXECUTE ON dbo.sp_LayThongTinHienTai TO QUANLY, THUTHU, DOCGIA;
GO
