/* ============================================================
   SCRIPT NẠP DỮ LIỆU MẪU CHO QLTV (11 BẢNG CHUẨN ĐỀ BÀI)
   Không thêm bất kỳ cột nào ngoài 11 bảng của đề thi.
   Chạy file này trên SSMS (SQL Server Management Studio).
   ============================================================ */

USE QLTV;
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 1. XÓA DỮ LIỆU CŨ THEO ĐÚNG THỨ TỰ RÀNG BUỘC KHÓA NGOẠI
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

-- 2. RESET LẠI CÁC CỘT IDENTITY VỀ 0 (NẾU BẢNG ĐÃ TỪNG CÓ DỮ LIỆU)
IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.NGONNGU') AND last_value IS NOT NULL)
    DBCC CHECKIDENT ('dbo.NGONNGU', RESEED, 0);
IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.NGANTU') AND last_value IS NOT NULL)
    DBCC CHECKIDENT ('dbo.NGANTU', RESEED, 0);
IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.TACGIA') AND last_value IS NOT NULL)
    DBCC CHECKIDENT ('dbo.TACGIA', RESEED, 0);
IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.DOCGIA') AND last_value IS NOT NULL)
    DBCC CHECKIDENT ('dbo.DOCGIA', RESEED, 0);
IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.NHANVIEN') AND last_value IS NOT NULL)
    DBCC CHECKIDENT ('dbo.NHANVIEN', RESEED, 0);
IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.PHIEUMUON') AND last_value IS NOT NULL)
    DBCC CHECKIDENT ('dbo.PHIEUMUON', RESEED, 0);
GO

-- 3. NHẬP DỮ LIỆU DANH MỤC

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

-- Bảng NHANVIEN (Đúng chuẩn 7 thuộc tính trong từ điển dữ liệu)
INSERT INTO dbo.NHANVIEN (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL) VALUES
(N'Nguyễn Trọng', N'Hoàng', 1, N'Hà Nội', '0987654321', 'admin@qltv.com'),
(N'Trần Thị', N'Mai', 0, N'Hà Nội', '0976543210', 'nv_mai@qltv.com'),
(N'Lê Văn', N'Nam', 1, N'Hải Phòng', '0965432109', 'nv_nam@qltv.com');

-- Bảng DOCGIA (Thẻ độc giả)
INSERT INTO dbo.DOCGIA (HODG, TENDG, EMAILDG, SOCMND, GIOITINH, NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG) VALUES
(N'Nguyễn Văn', N'An', 'an.nv@gmail.com', '001200123456', 1, '2002-05-15', N'Hà Nội', '0911111111', GETDATE(), DATEADD(YEAR, 2, GETDATE()), 1),
(N'Trần Thị', N'Bình', 'binh.tt@gmail.com', '001200654321', 0, '2003-08-20', N'Cầu Giấy, Hà Nội', '0922222222', GETDATE(), DATEADD(YEAR, 2, GETDATE()), 1),
(N'Lê Hoàng', N'Cường', 'cuong.lh@gmail.com', '001200987654', 1, '2001-12-10', N'Đống Đa, Hà Nội', '0933333333', GETDATE(), DATEADD(YEAR, 1, GETDATE()), 1);

-- Bảng ISBN (Đầu sách)
INSERT INTO dbo.ISBN (ISBN, TENSACH, KHOSACH, NOIDUNG, SOTRANG, GIA, HINHANHPATH, NGAYXUATBAN, LANXUATBAN, NHAXB, MANGONNGU, MATL) VALUES
('ISBN000001', N'Clean Code - Mã Sạch', '16x24', N'Hướng dẫn viết code sạch, dễ bảo trì', 450, 250000, 'cleancode.png', '2020-01-01', 1, N'NXB Thông tin & Truyền thông', 1, 'TL001'),
('ISBN000002', N'Đắc Nhân Tâm', '14x20', N'Nghệ thuật giao tiếp và thu phục lòng người', 320, 110000, 'dacnhantam.png', '2019-05-10', 5, N'NXB Tổng hợp TP.HCM', 1, 'TL005'),
('ISBN000003', N'Cho Tôi Xin Một Vé Đi Tuổi Thơ', '13x20', N'Truyện dài về ký ức tuổi thơ', 210, 85000, 've_di_tuoi_tho.png', '2021-03-15', 10, N'NXB Trẻ', 1, 'TL003');

-- Bảng TACGIA_SACH (Quan hệ N-N giữa Tác giả và Đầu sách)
INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES
(2, 'ISBN000001'), -- Robert C. Martin -> Clean Code
(3, 'ISBN000002'), -- Dale Carnegie -> Đắc Nhân Tâm
(1, 'ISBN000003'); -- Nguyễn Nhật Ánh -> Cho Tôi Xin Một Vé Đi Tuổi Thơ

-- Bảng SACH (Cuốn sách vật lý trong kho)
INSERT INTO dbo.SACH (MASACH, ISBN, TINHTRANG, CHOMUON, MANGANTU) VALUES
('S00101', 'ISBN000001', 1, 1, 1), -- Clean Code cuốn 1 (đang mượn)
('S00102', 'ISBN000001', 1, 0, 1), -- Clean Code cuốn 2 (sẵn sàng)
('S00201', 'ISBN000002', 1, 1, 3), -- Đắc Nhân Tâm cuốn 1 (đang mượn)
('S00301', 'ISBN000003', 1, 0, 4); -- Cho Tôi Xin Một Vé cuốn 1 (sẵn sàng)

-- Bảng PHIEUMUON
INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV) VALUES
(1, 1, DATEADD(DAY, -10, GETDATE()), 1), -- Độc giả An mượn 10 ngày trước (mang về)
(2, 1, DATEADD(DAY, -35, GETDATE()), 2); -- Độc giả Bình mượn 35 ngày trước (quá hạn 5 ngày)

-- Bảng CT_PHIEUMUON
INSERT INTO dbo.CT_PHIEUMUON (MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS) VALUES
(1, 'S00101', NULL, 1, 0, NULL), -- Phiếu 1 mượn S00101 chưa trả
(2, 'S00201', NULL, 1, 0, NULL); -- Phiếu 2 mượn S00201 chưa trả (quá hạn)
GO

-- Kiểm tra dữ liệu nhân viên
SELECT MANV, HONV + ' ' + TENNV AS HoTen, EMAIL, DIENTHOAI FROM dbo.NHANVIEN;
GO
