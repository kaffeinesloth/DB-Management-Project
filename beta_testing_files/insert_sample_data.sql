/* ============================================================
   SCRIPT THÊM DỮ LIỆU MẪU VÀ STORED PROCEDURE CHO QLTV
   Chạy file này trực tiếp trên SSMS (SQL Server Management Studio)
   ============================================================ */

USE QLTV;
GO

-- 1. Bổ sung các cột Đăng nhập & Vai trò vào bảng NHANVIEN (nếu chưa có)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.NHANVIEN') AND name = 'TENDANGNHAP')
BEGIN
    ALTER TABLE dbo.NHANVIEN ADD TENDANGNHAP VARCHAR(50) NULL;
END;
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.NHANVIEN') AND name = 'MATKHAU')
BEGIN
    ALTER TABLE dbo.NHANVIEN ADD MATKHAU VARCHAR(50) NULL;
END;
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.NHANVIEN') AND name = 'VAITRO')
BEGIN
    ALTER TABLE dbo.NHANVIEN ADD VAITRO NVARCHAR(50) DEFAULT N'Nhân viên' WITH VALUES;
END;
GO

-- 2. Tạo hoặc Cập nhật Stored Procedure sp_KiemTraDangNhap
CREATE OR ALTER PROCEDURE dbo.sp_KiemTraDangNhap
    @TenDangNhap VARCHAR(50),
    @MatKhau VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        MANV,
        RTRIM(HONV) + ' ' + RTRIM(TENNV) AS HoTen,
        ISNULL(VAITRO, N'Nhân viên') AS VaiTro,
        ISNULL(EMAIL, 'N/A') AS Email
    FROM dbo.NHANVIEN
    WHERE (TENDANGNHAP = @TenDangNhap OR EMAIL = @TenDangNhap)
      AND MATKHAU = @MatKhau;
END;
GO

-- 3. XÓA DỮ LIỆU CŨ THEO ĐÚNG THỨ TỰ KHÓA NGOẠI (NẾU CÓ)
DELETE FROM dbo.CT_PHIEUMUON;
DELETE FROM dbo.PHIEUMUON;
DELETE FROM dbo.TACGIA_SACH;
DELETE FROM dbo.SACH;
DELETE FROM dbo.ISBN;
DELETE FROM dbo.DOCGIA;
DELETE FROM dbo.NHANVIEN;
DELETE FROM dbo.TACGIA;
DELETE FROM dbo.NGANTU;
DELETE FROM dbo.NGONNGU;
DELETE FROM dbo.THELOAI;
GO

-- Reset lại các cột IDENTITY về 0
DBCC CHECKIDENT ('dbo.NGONNGU', RESEED, 0);
DBCC CHECKIDENT ('dbo.NGANTU', RESEED, 0);
DBCC CHECKIDENT ('dbo.TACGIA', RESEED, 0);
DBCC CHECKIDENT ('dbo.DOCGIA', RESEED, 0);
DBCC CHECKIDENT ('dbo.NHANVIEN', RESEED, 0);
DBCC CHECKIDENT ('dbo.PHIEUMUON', RESEED, 0);
GO

-- 4. NHẬP DỮ LIỆU MẪU

-- Bảng THELOAI
INSERT INTO dbo.THELOAI (MATL, THELOAI) VALUES
('TL001', N'Công nghệ thông tin'),
('TL002', N'Kinh tế - Quản lý'),
('TL003', N'Văn học trong nước'),
('TL004', N'Văn học nước ngoài'),
('TL005', N'Kỹ năng sống');

-- Bảng NGONNGU
INSERT INTO dbo.NGONNGU (NGONNGU) VALUES
(N'Tiếng Việt'),
(N'Tiếng Anh'),
(N'Tiếng Nhật');

-- Bảng NGANTU
INSERT INTO dbo.NGANTU (MOTA, KE) VALUES
(N'Tủ sách CNTT tầng 1', N'Kệ A1'),
(N'Tủ sách CNTT tầng 1', N'Kệ A2'),
(N'Tủ sách Kinh tế tầng 2', N'Kệ B1'),
(N'Tủ sách Văn học tầng 2', N'Kệ C1');

-- Bảng TACGIA
INSERT INTO dbo.TACGIA (HOTENTG, DIACHITG, DIENTHOAITG) VALUES
(N'Nguyễn Nhật Ánh', N'TP. Hồ Chí Minh', '0901234567'),
(N'Robert C. Martin', N'USA', '0912345678'),
(N'Dale Carnegie', N'USA', '0923456789'),
(N'Phạm Hữu Cường', N'Hà Nội', '0934567890');

-- Bảng NHANVIEN (Có tài khoản đăng nhập)
INSERT INTO dbo.NHANVIEN (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL, TENDANGNHAP, MATKHAU, VAITRO) VALUES
(N'Nguyễn Trọng', N'Hoàng', 1, N'Hà Nội', '0987654321', 'admin@qltv.com', 'admin', 'Admin@123', N'Quản lý'),
(N'Trần Thị', N'Mai', 0, N'Hà Nội', '0976543210', 'mai.tt@qltv.com', 'nv_mai', '123456', N'Thu thư'),
(N'Lê Văn', N'Nam', 1, N'Hải Phòng', '0965432109', 'nam.lv@qltv.com', 'nv_nam', '123456', N'Thu thư');

-- Bảng DOCGIA
INSERT INTO dbo.DOCGIA (HODG, TENDG, EMAILDG, SOCMND, GIOITINH, NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG) VALUES
(N'Nguyễn Văn', N'An', 'an.nv@gmail.com', '001200123456', 1, '2002-05-15', N'Hà Nội', '0911111111', GETDATE(), DATEADD(YEAR, 2, GETDATE()), 1),
(N'Trần Thị', N'Bình', 'binh.tt@gmail.com', '001200654321', 0, '2003-08-20', N'Cầu Giấy, Hà Nội', '0922222222', GETDATE(), DATEADD(YEAR, 2, GETDATE()), 1),
(N'Lê Hoàng', N'Cường', 'cuong.lh@gmail.com', '001200987654', 1, '2001-12-10', N'Đống Đa, Hà Nội', '0933333333', GETDATE(), DATEADD(YEAR, 1, GETDATE()), 1);

-- Bảng ISBN (Đầu sách)
INSERT INTO dbo.ISBN (ISBN, TENSACH, KHOSACH, NOIDUNG, SOTRANG, GIA, HINHANHPATH, NGAYXUATBAN, LANXUATBAN, NHAXB, MANGONNGU, MATL) VALUES
('ISBN000001', N'Clean Code - Mã Sạch', '16x24', N'Hướng dẫn viết code sạch, dễ bảo trì', 450, 250000, 'cleancode.png', '2020-01-01', 1, N'NXB Thông tin & Truyền thông', 1, 'TL001'),
('ISBN000002', N'Đắc Nhân Tâm', '14x20', N'Nghệ thuật giao tiếp và thu phục lòng người', 320, 110000, 'dacnhantam.png', '2019-05-10', 5, N'NXB Tổng hợp TP.HCM', 1, 'TL005'),
('ISBN000003', N'Cho Tôi Xin Một Vé Đi Tuổi Thơ', '13x20', N'Truyện dài về ký ức tuổi thơ', 210, 85000, 've_di_tuoi_tho.png', '2021-03-15', 10, N'NXB Trẻ', 1, 'TL003');

-- Bảng TACGIA_SACH
INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES
(2, 'ISBN000001'), -- Robert C. Martin -> Clean Code
(3, 'ISBN000002'), -- Dale Carnegie -> Đắc Nhân Tâm
(1, 'ISBN000003'); -- Nguyễn Nhật Ánh -> Cho Tôi Xin Một Vé Đi Tuổi Thơ

-- Bảng SACH (Cuốn sách vật lý)
INSERT INTO dbo.SACH (MASACH, ISBN, TINHTRANG, CHOMUON, MANGANTU) VALUES
('S00101', 'ISBN000001', 1, 1, 1), -- Cuốn Clean Code 1 (đã cho mượn)
('S00102', 'ISBN000001', 1, 0, 1), -- Cuốn Clean Code 2 (sẵn sàng)
('S00201', 'ISBN000002', 1, 1, 3), -- Cuốn Đắc Nhân Tâm 1 (đã cho mượn)
('S00301', 'ISBN000003', 1, 0, 4); -- Cuốn Tuổi Thơ 1 (sẵn sàng)

-- Bảng PHIEUMUON
INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV) VALUES
(1, 1, DATEADD(DAY, -10, GETDATE()), 1), -- Độc giả An mượn 10 ngày trước (mang về)
(2, 1, DATEADD(DAY, -35, GETDATE()), 2); -- Độc giả Bình mượn 35 ngày trước (quá hạn 5 ngày)

-- Bảng CT_PHIEUMUON
INSERT INTO dbo.CT_PHIEUMUON (MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS) VALUES
(1, 'S00101', NULL, 1, 0, NULL), -- Phiếu 1 mượn S00101 chưa trả
(2, 'S00201', NULL, 1, 0, NULL); -- Phiếu 2 mượn S00201 chưa trả (quá hạn)
GO

-- Kiểm tra dữ liệu nhân viên dùng để đăng nhập
SELECT MANV, HONV + ' ' + TENNV AS HoTen, TENDANGNHAP, MATKHAU, VAITRO, EMAIL FROM dbo.NHANVIEN;
GO
