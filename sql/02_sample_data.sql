/*
    Library Management System - sample data
    Run after 01_create_tables.sql.

    The script is rerunnable: existing records are matched by stable business
    values before insertion. It creates 30 physical books plus related data.
*/

USE [LibraryManagement];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO dbo.THELOAI (MATL, THELOAI)
    SELECT source.MATL, source.THELOAI
    FROM (VALUES
        ('TL001', N'Văn học'),
        ('TL002', N'Khoa học'),
        ('TL003', N'Công nghệ thông tin'),
        ('TL004', N'Lịch sử'),
        ('TL005', N'Kỹ năng sống')
    ) AS source (MATL, THELOAI)
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.THELOAI AS target WHERE target.MATL = source.MATL
    );

    INSERT INTO dbo.NGONNGU (NGONNGU)
    SELECT source.NGONNGU
    FROM (VALUES
        (N'Tiếng Việt'),
        (N'Tiếng Anh'),
        (N'Tiếng Pháp'),
        (N'Tiếng Nhật')
    ) AS source (NGONNGU)
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.NGONNGU AS target WHERE target.NGONNGU = source.NGONNGU
    );

    INSERT INTO dbo.NGANTU (MOTA, KE)
    SELECT source.MOTA, source.KE
    FROM (VALUES
        (N'Tầng 1 - Khu A', N'Kệ A1'),
        (N'Tầng 1 - Khu A', N'Kệ A2'),
        (N'Tầng 1 - Khu B', N'Kệ B1'),
        (N'Tầng 2 - Khu C', N'Kệ C1'),
        (N'Tầng 2 - Khu C', N'Kệ C2'),
        (N'Tầng 2 - Khu D', N'Kệ D1')
    ) AS source (MOTA, KE)
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.NGANTU AS target
        WHERE target.MOTA = source.MOTA AND target.KE = source.KE
    );

    INSERT INTO dbo.TACGIA (HOTENTG, DIACHITG, DIENTHOAITG)
    SELECT source.HOTENTG, source.DIACHITG, source.DIENTHOAITG
    FROM (VALUES
        (N'Nguyễn Nhật Ánh', N'Thành phố Hồ Chí Minh', '0901000001'),
        (N'Tô Hoài', N'Hà Nội', '0901000002'),
        (N'Nam Cao', N'Hà Nam', '0901000003'),
        (N'Võ Quảng', N'Quảng Nam', '0901000004'),
        (N'Trần Đức Tiến', N'Hà Nội', '0901000005'),
        (N'Robert C. Martin', N'United States', '0901000006'),
        (N'Andrew S. Tanenbaum', N'Netherlands', '0901000007'),
        (N'Yuval Noah Harari', N'Israel', '0901000008'),
        (N'Dale Carnegie', N'United States', '0901000009'),
        (N'Antoine de Saint-Exupéry', N'France', '0901000010'),
        (N'Stephen Hawking', N'United Kingdom', '0901000011'),
        (N'Daniel Kahneman', N'United States', '0901000012'),
        (N'Nhóm biên soạn', N'Việt Nam', '0901000013')
    ) AS source (HOTENTG, DIACHITG, DIENTHOAITG)
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.TACGIA AS target WHERE target.HOTENTG = source.HOTENTG
    );

    INSERT INTO dbo.DOCGIA
    (
        HODG, TENDG, EMAILDG, SOCMND, GIOITINH, NGAYSINH,
        DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
    )
    SELECT
        source.HODG, source.TENDG, source.EMAILDG, source.SOCMND,
        source.GIOITINH, CONVERT(SMALLDATETIME, source.NGAYSINH, 126),
        source.DIACHI, source.DIENTHOAI,
        CONVERT(SMALLDATETIME, source.NGAYLAMTHE, 126),
        CONVERT(SMALLDATETIME, source.NGAYHETHAN, 126), source.HOATDONG
    FROM (VALUES
        (N'Nguyễn', N'An', N'an.nguyen@example.com', '079201000001', 1, '2001-03-12T00:00:00', N'Quận 1, TP.HCM', '0912000001', '2025-09-01T00:00:00', '2027-09-01T00:00:00', 1),
        (N'Trần', N'Bình', N'binh.tran@example.com', '079201000002', 1, '2002-07-25T00:00:00', N'Quận 3, TP.HCM', '0912000002', '2025-09-01T00:00:00', '2027-09-01T00:00:00', 1),
        (N'Lê', N'Chi', N'chi.le@example.com', '079201000003', 0, '2003-11-08T00:00:00', N'Thủ Đức, TP.HCM', '0912000003', '2025-09-02T00:00:00', '2027-09-02T00:00:00', 1),
        (N'Phạm', N'Dũng', N'dung.pham@example.com', '079201000004', 1, '2001-01-19T00:00:00', N'Quận 5, TP.HCM', '0912000004', '2025-09-02T00:00:00', '2027-09-02T00:00:00', 1),
        (N'Hoàng', N'Giang', N'giang.hoang@example.com', '079201000005', 0, '2002-05-30T00:00:00', N'Bình Thạnh, TP.HCM', '0912000005', '2025-09-03T00:00:00', '2027-09-03T00:00:00', 1),
        (N'Vũ', N'Hà', N'ha.vu@example.com', '079201000006', 0, '2000-09-14T00:00:00', N'Quận 7, TP.HCM', '0912000006', '2025-09-03T00:00:00', '2027-09-03T00:00:00', 1),
        (N'Đặng', N'Khôi', N'khoi.dang@example.com', '079201000007', 1, '2003-04-22T00:00:00', N'Gò Vấp, TP.HCM', '0912000007', '2025-09-04T00:00:00', '2027-09-04T00:00:00', 1),
        (N'Bùi', N'Lan', N'lan.bui@example.com', '079201000008', 0, '2001-12-01T00:00:00', N'Quận 10, TP.HCM', '0912000008', '2025-09-04T00:00:00', '2027-09-04T00:00:00', 1),
        (N'Đỗ', N'Minh', N'minh.do@example.com', '079201000009', 1, '2002-08-17T00:00:00', N'Tân Bình, TP.HCM', '0912000009', '2025-09-05T00:00:00', '2027-09-05T00:00:00', 1),
        (N'Ngô', N'Nga', N'nga.ngo@example.com', '079201000010', 0, '2000-06-09T00:00:00', N'Phú Nhuận, TP.HCM', '0912000010', '2025-09-05T00:00:00', '2027-09-05T00:00:00', 1),
        (N'Dương', N'Phúc', N'phuc.duong@example.com', '079201000011', 1, '2003-02-11T00:00:00', N'Quận 8, TP.HCM', '0912000011', '2025-09-06T00:00:00', '2027-09-06T00:00:00', 1),
        (N'Phan', N'Quỳnh', N'quynh.phan@example.com', '079201000012', 0, '2002-10-27T00:00:00', N'Quận 11, TP.HCM', '0912000012', '2025-09-06T00:00:00', '2027-09-06T00:00:00', 1)
    ) AS source
    (
        HODG, TENDG, EMAILDG, SOCMND, GIOITINH, NGAYSINH,
        DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
    )
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.DOCGIA AS target WHERE target.SOCMND = source.SOCMND
    );

    INSERT INTO dbo.NHANVIEN (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL)
    SELECT source.HONV, source.TENNV, source.GIOITINH,
           source.DIACHI, source.DIENTHOAI, source.EMAIL
    FROM (VALUES
        (N'Nguyễn', N'Hương', 0, N'Quận 1, TP.HCM', '0923000001', 'huong.nguyen@library.local'),
        (N'Trần', N'Long', 1, N'Quận 3, TP.HCM', '0923000002', 'long.tran@library.local'),
        (N'Lê', N'Mai', 0, N'Quận 5, TP.HCM', '0923000003', 'mai.le@library.local'),
        (N'Phạm', N'Nam', 1, N'Quận 7, TP.HCM', '0923000004', 'nam.pham@library.local'),
        (N'Võ', N'Oanh', 0, N'Thủ Đức, TP.HCM', '0923000005', 'oanh.vo@library.local')
    ) AS source (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL)
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.NHANVIEN AS target WHERE target.EMAIL = source.EMAIL
    );

    INSERT INTO dbo.ISBN
    (
        ISBN, TENSACH, KHOSACH, NOIDUNG, HINHANHPATH, NGAYXUATBAN,
        LANXUATBAN, SOTRANG, GIA, NHAXB, MANGONNGU, MATL
    )
    SELECT
        source.ISBN, source.TENSACH, source.KHOSACH, source.NOIDUNG,
        source.HINHANHPATH, CONVERT(SMALLDATETIME, source.NGAYXUATBAN, 126),
        source.LANXUATBAN, source.SOTRANG, source.GIA, source.NHAXB,
        language.MANGONNGU, source.MATL
    FROM (VALUES
        ('9786041001', N'Mắt biếc', N'13x20', N'Tiểu thuyết về tuổi học trò và những ký ức trong trẻo.', N'images/mat-biec.jpg', '2019-01-15T00:00:00', 12, 300, 95000, N'Nhà xuất bản Trẻ', N'Tiếng Việt', 'TL001'),
        ('9786041002', N'Cho tôi xin một vé đi tuổi thơ', N'13x20', N'Câu chuyện về thế giới tuổi thơ.', N'images/ve-tuoi-tho.jpg', '2018-06-20T00:00:00', 18, 208, 85000, N'Nhà xuất bản Trẻ', N'Tiếng Việt', 'TL001'),
        ('9786041003', N'Dế Mèn phiêu lưu ký', N'14x21', N'Tác phẩm văn học thiếu nhi kinh điển.', N'images/de-men.jpg', '2020-03-10T00:00:00', 25, 160, 70000, N'Nhà xuất bản Kim Đồng', N'Tiếng Việt', 'TL001'),
        ('9786041004', N'Chí Phèo', N'13x20', N'Truyện ngắn hiện thực Việt Nam.', N'images/chi-pheo.jpg', '2021-05-12T00:00:00', 8, 144, 60000, N'Nhà xuất bản Văn học', N'Tiếng Việt', 'TL001'),
        ('9786041005', N'Quê nội', N'14x21', N'Tác phẩm viết về tuổi thơ và quê hương.', N'images/que-noi.jpg', '2020-08-01T00:00:00', 6, 220, 78000, N'Nhà xuất bản Kim Đồng', N'Tiếng Việt', 'TL001'),
        ('9786041006', N'Xóm Bờ Giậu', N'14x21', N'Những câu chuyện gần gũi về thiên nhiên.', N'images/xom-bo-giau.jpg', '2022-02-18T00:00:00', 3, 180, 82000, N'Nhà xuất bản Kim Đồng', N'Tiếng Việt', 'TL001'),
        ('9786041007', N'Clean Code', N'16x24', N'Các nguyên tắc viết mã nguồn rõ ràng và dễ bảo trì.', N'images/clean-code.jpg', '2008-08-01T00:00:00', 1, 464, 320000, N'Prentice Hall', N'Tiếng Anh', 'TL003'),
        ('9786041008', N'Computer Networks', N'16x24', N'Kiến thức nền tảng về mạng máy tính.', N'images/networks.jpg', '2021-03-09T00:00:00', 6, 960, 450000, N'Pearson', N'Tiếng Anh', 'TL003'),
        ('9786041009', N'Sapiens', N'15x23', N'Lược sử loài người từ thời tiền sử đến hiện đại.', N'images/sapiens.jpg', '2015-02-10T00:00:00', 1, 512, 250000, N'Harper', N'Tiếng Anh', 'TL004'),
        ('9786041010', N'Đắc nhân tâm', N'14x21', N'Những nguyên tắc giao tiếp và ứng xử.', N'images/dac-nhan-tam.jpg', '2019-04-05T00:00:00', 10, 320, 110000, N'Nhà xuất bản Tổng hợp', N'Tiếng Việt', 'TL005'),
        ('9786041011', N'Le Petit Prince', N'13x20', N'Câu chuyện giàu tính nhân văn về Hoàng tử bé.', N'images/petit-prince.jpg', '2016-09-01T00:00:00', 4, 128, 140000, N'Gallimard', N'Tiếng Pháp', 'TL001'),
        ('9786041012', N'Vũ trụ trong vỏ hạt dẻ', N'16x24', N'Khám phá các ý tưởng lớn của vật lý hiện đại.', N'images/vu-tru.jpg', '2018-11-11T00:00:00', 2, 240, 180000, N'Nhà xuất bản Trẻ', N'Tiếng Việt', 'TL002'),
        ('9786041013', N'Lược sử thời gian', N'16x24', N'Giới thiệu vũ trụ học cho độc giả phổ thông.', N'images/luoc-su.jpg', '2017-07-14T00:00:00', 5, 256, 190000, N'Nhà xuất bản Trẻ', N'Tiếng Việt', 'TL002'),
        ('9786041014', N'Tư duy nhanh và chậm', N'15x23', N'Khám phá hai hệ thống chi phối tư duy con người.', N'images/tu-duy.jpg', '2020-10-21T00:00:00', 7, 612, 269000, N'Nhà xuất bản Thế giới', N'Tiếng Việt', 'TL005'),
        ('9786041015', N'Python căn bản', N'16x24', N'Nhập môn lập trình bằng ngôn ngữ Python.', N'images/python.jpg', '2023-01-09T00:00:00', 2, 360, 175000, N'Nhà xuất bản Thông tin', N'Tiếng Việt', 'TL003')
    ) AS source
    (
        ISBN, TENSACH, KHOSACH, NOIDUNG, HINHANHPATH, NGAYXUATBAN,
        LANXUATBAN, SOTRANG, GIA, NHAXB, NGONNGU, MATL
    )
    INNER JOIN dbo.NGONNGU AS language ON language.NGONNGU = source.NGONNGU
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.ISBN AS target WHERE target.ISBN = source.ISBN
    );

    INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN)
    SELECT author.MATACGIA, source.ISBN
    FROM (VALUES
        (N'Nguyễn Nhật Ánh', '9786041001'),
        (N'Nguyễn Nhật Ánh', '9786041002'),
        (N'Tô Hoài', '9786041003'),
        (N'Nam Cao', '9786041004'),
        (N'Võ Quảng', '9786041005'),
        (N'Trần Đức Tiến', '9786041006'),
        (N'Robert C. Martin', '9786041007'),
        (N'Andrew S. Tanenbaum', '9786041008'),
        (N'Yuval Noah Harari', '9786041009'),
        (N'Dale Carnegie', '9786041010'),
        (N'Antoine de Saint-Exupéry', '9786041011'),
        (N'Stephen Hawking', '9786041012'),
        (N'Stephen Hawking', '9786041013'),
        (N'Daniel Kahneman', '9786041014'),
        (N'Nhóm biên soạn', '9786041015')
    ) AS source (HOTENTG, ISBN)
    INNER JOIN dbo.TACGIA AS author ON author.HOTENTG = source.HOTENTG
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.TACGIA_SACH AS target
        WHERE target.MATACGIA = author.MATACGIA AND target.ISBN = source.ISBN
    );

    INSERT INTO dbo.SACH (MASACH, ISBN, TINHTRANG, CHOMUON, MANGANTU)
    SELECT source.MASACH, source.ISBN, source.TINHTRANG, 0, shelf.MANGANTU
    FROM (VALUES
        ('S0001', '9786041001', 1, N'Tầng 1 - Khu A', N'Kệ A1'),
        ('S0002', '9786041001', 1, N'Tầng 1 - Khu A', N'Kệ A1'),
        ('S0003', '9786041002', 1, N'Tầng 1 - Khu A', N'Kệ A1'),
        ('S0004', '9786041002', 1, N'Tầng 1 - Khu A', N'Kệ A1'),
        ('S0005', '9786041003', 1, N'Tầng 1 - Khu A', N'Kệ A2'),
        ('S0006', '9786041003', 0, N'Tầng 1 - Khu A', N'Kệ A2'),
        ('S0007', '9786041004', 1, N'Tầng 1 - Khu A', N'Kệ A2'),
        ('S0008', '9786041004', 1, N'Tầng 1 - Khu A', N'Kệ A2'),
        ('S0009', '9786041005', 1, N'Tầng 1 - Khu B', N'Kệ B1'),
        ('S0010', '9786041005', 1, N'Tầng 1 - Khu B', N'Kệ B1'),
        ('S0011', '9786041006', 1, N'Tầng 1 - Khu B', N'Kệ B1'),
        ('S0012', '9786041006', 1, N'Tầng 1 - Khu B', N'Kệ B1'),
        ('S0013', '9786041007', 1, N'Tầng 2 - Khu C', N'Kệ C1'),
        ('S0014', '9786041007', 1, N'Tầng 2 - Khu C', N'Kệ C1'),
        ('S0015', '9786041008', 1, N'Tầng 2 - Khu C', N'Kệ C1'),
        ('S0016', '9786041008', 1, N'Tầng 2 - Khu C', N'Kệ C1'),
        ('S0017', '9786041009', 1, N'Tầng 2 - Khu C', N'Kệ C2'),
        ('S0018', '9786041009', 1, N'Tầng 2 - Khu C', N'Kệ C2'),
        ('S0019', '9786041010', 1, N'Tầng 2 - Khu C', N'Kệ C2'),
        ('S0020', '9786041010', 1, N'Tầng 2 - Khu C', N'Kệ C2'),
        ('S0021', '9786041011', 1, N'Tầng 1 - Khu B', N'Kệ B1'),
        ('S0022', '9786041011', 1, N'Tầng 1 - Khu B', N'Kệ B1'),
        ('S0023', '9786041012', 1, N'Tầng 2 - Khu D', N'Kệ D1'),
        ('S0024', '9786041012', 1, N'Tầng 2 - Khu D', N'Kệ D1'),
        ('S0025', '9786041013', 1, N'Tầng 2 - Khu D', N'Kệ D1'),
        ('S0026', '9786041013', 1, N'Tầng 2 - Khu D', N'Kệ D1'),
        ('S0027', '9786041014', 1, N'Tầng 2 - Khu C', N'Kệ C2'),
        ('S0028', '9786041014', 1, N'Tầng 2 - Khu C', N'Kệ C2'),
        ('S0029', '9786041015', 1, N'Tầng 2 - Khu C', N'Kệ C1'),
        ('S0030', '9786041015', 1, N'Tầng 2 - Khu C', N'Kệ C1')
    ) AS source (MASACH, ISBN, TINHTRANG, MOTA, KE)
    INNER JOIN dbo.NGANTU AS shelf
        ON shelf.MOTA = source.MOTA AND shelf.KE = source.KE
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.SACH AS target WHERE target.MASACH = source.MASACH
    );

    INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV)
    SELECT reader.MADG, source.HINHTHUC,
           CONVERT(SMALLDATETIME, source.NGAYMUON, 126), employee.MANV
    FROM (VALUES
        ('079201000001', 1, '2026-08-01T09:00:00', 'huong.nguyen@library.local'),
        ('079201000002', 1, '2026-08-05T10:15:00', 'long.tran@library.local'),
        ('079201000003', 0, '2026-08-10T14:00:00', 'mai.le@library.local'),
        ('079201000004', 1, '2026-08-15T08:30:00', 'nam.pham@library.local'),
        ('079201000005', 1, '2026-09-01T13:20:00', 'oanh.vo@library.local'),
        ('079201000006', 0, '2026-09-10T15:45:00', 'huong.nguyen@library.local'),
        ('079201000007', 1, '2026-09-15T09:10:00', 'long.tran@library.local'),
        ('079201000008', 1, '2026-10-01T11:00:00', 'mai.le@library.local'),
        ('079201000009', 1, '2026-10-03T09:30:00', 'nam.pham@library.local'),
        ('079201000010', 0, '2026-10-04T14:15:00', 'oanh.vo@library.local')
    ) AS source (SOCMND, HINHTHUC, NGAYMUON, EMAILNV)
    INNER JOIN dbo.DOCGIA AS reader ON reader.SOCMND = source.SOCMND
    INNER JOIN dbo.NHANVIEN AS employee ON employee.EMAIL = source.EMAILNV
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.PHIEUMUON AS target
        WHERE target.MADG = reader.MADG
          AND target.NGAYMUON = CONVERT(SMALLDATETIME, source.NGAYMUON, 126)
    );

    INSERT INTO dbo.CT_PHIEUMUON
    (
        MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS
    )
    SELECT
        loan.MAPHIEU, source.MASACH,
        CONVERT(SMALLDATETIME, source.NGAYTRA, 126),
        source.TINHTRANGMUON, source.TRA, receiver.MANV
    FROM (VALUES
        ('079201000001', '2026-08-01T09:00:00', 'S0001', '2026-08-20T10:00:00', 1, 1, 'long.tran@library.local'),
        ('079201000001', '2026-08-01T09:00:00', 'S0013', '2026-08-20T10:00:00', 1, 1, 'long.tran@library.local'),
        ('079201000002', '2026-08-05T10:15:00', 'S0003', '2026-09-12T09:00:00', 1, 1, 'mai.le@library.local'),
        ('079201000003', '2026-08-10T14:00:00', 'S0007', '2026-08-10T16:30:00', 1, 1, 'mai.le@library.local'),
        ('079201000004', '2026-08-15T08:30:00', 'S0015', '2026-09-01T11:30:00', 1, 1, 'nam.pham@library.local'),
        ('079201000005', '2026-09-01T13:20:00', 'S0017', '2026-09-28T14:00:00', 1, 1, 'oanh.vo@library.local'),
        ('079201000006', '2026-09-10T15:45:00', 'S0019', '2026-09-10T17:00:00', 1, 1, 'huong.nguyen@library.local'),
        ('079201000007', '2026-09-15T09:10:00', 'S0021', '2026-10-02T10:00:00', 1, 1, 'long.tran@library.local'),
        ('079201000008', '2026-10-01T11:00:00', 'S0002', NULL, 1, 0, NULL),
        ('079201000008', '2026-10-01T11:00:00', 'S0005', NULL, 1, 0, NULL),
        ('079201000009', '2026-10-03T09:30:00', 'S0011', NULL, 1, 0, NULL),
        ('079201000010', '2026-10-04T14:15:00', 'S0023', '2026-10-04T16:00:00', 1, 1, 'oanh.vo@library.local')
    ) AS source
    (
        SOCMND, NGAYMUON, MASACH, NGAYTRA, TINHTRANGMUON, TRA, EMAILNVNS
    )
    INNER JOIN dbo.DOCGIA AS reader ON reader.SOCMND = source.SOCMND
    INNER JOIN dbo.PHIEUMUON AS loan
        ON loan.MADG = reader.MADG
       AND loan.NGAYMUON = CONVERT(SMALLDATETIME, source.NGAYMUON, 126)
    LEFT JOIN dbo.NHANVIEN AS receiver ON receiver.EMAIL = source.EMAILNVNS
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.CT_PHIEUMUON AS target
        WHERE target.MAPHIEU = loan.MAPHIEU AND target.MASACH = source.MASACH
    );

    UPDATE book
    SET CHOMUON = CASE
        WHEN EXISTS
        (
            SELECT 1
            FROM dbo.CT_PHIEUMUON AS detail
            WHERE detail.MASACH = book.MASACH AND detail.TRA = 0
        ) THEN 1 ELSE 0 END
    FROM dbo.SACH AS book
    WHERE book.MASACH LIKE 'S[0-9][0-9][0-9][0-9]';

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

SELECT N'THELOAI' AS TENBANG, COUNT(*) AS SOLUONG FROM dbo.THELOAI
UNION ALL SELECT N'NGONNGU', COUNT(*) FROM dbo.NGONNGU
UNION ALL SELECT N'NGANTU', COUNT(*) FROM dbo.NGANTU
UNION ALL SELECT N'TACGIA', COUNT(*) FROM dbo.TACGIA
UNION ALL SELECT N'DOCGIA', COUNT(*) FROM dbo.DOCGIA
UNION ALL SELECT N'NHANVIEN', COUNT(*) FROM dbo.NHANVIEN
UNION ALL SELECT N'ISBN', COUNT(*) FROM dbo.ISBN
UNION ALL SELECT N'SACH', COUNT(*) FROM dbo.SACH
UNION ALL SELECT N'TACGIA_SACH', COUNT(*) FROM dbo.TACGIA_SACH
UNION ALL SELECT N'PHIEUMUON', COUNT(*) FROM dbo.PHIEUMUON
UNION ALL SELECT N'CT_PHIEUMUON', COUNT(*) FROM dbo.CT_PHIEUMUON;
GO
