/*
    Transactional smoke tests for the teacher-specified borrowing rules.

    Every data change is rolled back. Run through docker/smoke-test.sh after
    database-init exits successfully.
*/

:on error exit

USE [LibraryManagement];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

/* A lost card can be deactivated and replaced with a new MADG. */
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE dbo.DOCGIA
    SET HOATDONG = 0
    WHERE SOCMND = '079201000011' AND HOATDONG = 1;

    INSERT INTO dbo.DOCGIA
    (
        HODG, TENDG, EMAILDG, SOCMND, GIOITINH, NGAYSINH,
        DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
    )
    SELECT
        HODG, TENDG, EMAILDG, SOCMND, GIOITINH, NGAYSINH,
        DIACHI, DIENTHOAI, '2026-10-20', '2027-10-20', 1
    FROM dbo.DOCGIA
    WHERE SOCMND = '079201000011' AND HOATDONG = 0;

    IF (SELECT COUNT(*) FROM dbo.DOCGIA WHERE SOCMND = '079201000011') <> 2
    BEGIN
        ;THROW 50200, 'Replacement-card history was not preserved.', 1;
    END;

    IF (SELECT COUNT(*) FROM dbo.DOCGIA WHERE SOCMND = '079201000011' AND HOATDONG = 1) <> 1
    BEGIN
        ;THROW 50201, 'Replacement-card active-state rule failed.', 1;
    END;

    ROLLBACK TRANSACTION;
    SELECT N'PASS' AS Result, N'Replacement card' AS TestName;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

/* A third active book is allowed; a fourth is rejected. */
BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV)
    VALUES (8, 1, '2026-10-15', 1);

    DECLARE @LimitTestLoan BIGINT = SCOPE_IDENTITY();

    INSERT INTO dbo.CT_PHIEUMUON
        (MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS)
    VALUES (@LimitTestLoan, 'S0004', NULL, 1, 0, NULL);

    IF (SELECT CHOMUON FROM dbo.SACH WHERE MASACH = 'S0004') <> 1
    BEGIN
        ;THROW 50202, 'Loan-state synchronization failed.', 1;
    END;

    INSERT INTO dbo.CT_PHIEUMUON
        (MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS)
    VALUES (@LimitTestLoan, 'S0008', NULL, 1, 0, NULL);

    ROLLBACK TRANSACTION;
    ;THROW 50203, 'A fourth active book was incorrectly accepted.', 1;
END TRY
BEGIN CATCH
    DECLARE @LimitError INT = ERROR_NUMBER();
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    IF @LimitError <> 50013
    BEGIN
        THROW;
    END;
    SELECT N'PASS' AS Result, N'Maximum three active books' AS TestName;
END CATCH;

/* An unusable physical book is rejected. */
BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV)
    VALUES (1, 1, '2026-10-15', 1);

    DECLARE @DamagedBookLoan BIGINT = SCOPE_IDENTITY();

    INSERT INTO dbo.CT_PHIEUMUON
        (MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS)
    VALUES (@DamagedBookLoan, 'S0006', NULL, 1, 0, NULL);

    ROLLBACK TRANSACTION;
    ;THROW 50204, 'A damaged book was incorrectly accepted.', 1;
END TRY
BEGIN CATCH
    DECLARE @DamagedError INT = ERROR_NUMBER();
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    IF @DamagedError <> 50011
    BEGIN
        THROW;
    END;
    SELECT N'PASS' AS Result, N'Damaged book rejection' AS TestName;
END CATCH;

/* A physical copy cannot have two active loans. */
BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV)
    VALUES (1, 1, '2026-10-15', 1);

    DECLARE @DuplicateBookLoan BIGINT = SCOPE_IDENTITY();

    INSERT INTO dbo.CT_PHIEUMUON
        (MAPHIEU, MASACH, NGAYTRA, TINHTRANGMUON, TRA, MANVNS)
    VALUES (@DuplicateBookLoan, 'S0002', NULL, 1, 0, NULL);

    ROLLBACK TRANSACTION;
    ;THROW 50205, 'A duplicate active loan was incorrectly accepted.', 1;
END TRY
BEGIN CATCH
    DECLARE @DuplicateError INT = ERROR_NUMBER();
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    IF @DuplicateError <> 50012
    BEGIN
        THROW;
    END;
    SELECT N'PASS' AS Result, N'Duplicate active loan rejection' AS TestName;
END CATCH;

/* Returning a book immediately makes the physical copy available. */
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE dbo.CT_PHIEUMUON
    SET TRA = 1, NGAYTRA = '2026-10-20', MANVNS = 1
    WHERE MASACH = 'S0002' AND TRA = 0;

    IF (SELECT CHOMUON FROM dbo.SACH WHERE MASACH = 'S0002') <> 0
    BEGIN
        ;THROW 50206, 'Returned-book synchronization failed.', 1;
    END;

    ROLLBACK TRANSACTION;
    SELECT N'PASS' AS Result, N'Returned-book synchronization' AS TestName;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

/* S0003 was returned eight days after its 30-day due date. */
IF NOT EXISTS
(
    SELECT 1
    FROM dbo.v_CHITIET_MUONTRA
    WHERE MASACH = 'S0003'
      AND SONGAYQUAHAN = 8
      AND TIENPHATQUAHAN = 4000
)
BEGIN
    ;THROW 50207, 'The 30-day overdue fine calculation is incorrect.', 1;
END;

IF (SELECT COUNT(*) FROM dbo.v_TANSUAT_SU_DUNG_SACH) <> 15
BEGIN
    ;THROW 50208, 'The book-frequency report does not include every title.', 1;
END;

SELECT N'PASS' AS Result, N'Overdue fine and frequency reports' AS TestName;
/* Reports & Statistics (06_reports.sql). Dates are fixed so results do not
   depend on the day the test runs. */

/* As of 2026-09-10 only S0003 (borrowed 2026-08-05, due 2026-09-04) is out. */
IF (SELECT COUNT(*) FROM dbo.fn_BaoCao_QuaHan('2026-09-10')) <> 1
   OR NOT EXISTS
   (
       SELECT 1 FROM dbo.fn_BaoCao_QuaHan('2026-09-10')
       WHERE MASACH = 'S0003' AND SONGAYQUAHAN = 6 AND TIENPHAT = 3000
   )
BEGIN
    ;THROW 50209, 'The as-of overdue report is incorrect for 2026-09-10.', 1;
END;

/* As of 2026-11-10: S0002 and S0005 are 10 days late, S0011 is 8 days late. */
IF (SELECT COUNT(*) FROM dbo.fn_BaoCao_QuaHan('2026-11-10')) <> 3
   OR (SELECT SUM(TIENPHAT) FROM dbo.fn_BaoCao_QuaHan('2026-11-10')) <> 14000
BEGIN
    ;THROW 50210, 'The as-of overdue report is incorrect for 2026-11-10.', 1;
END;

/* Q3 2026 had 8 loan lines across 8 titles; all 15 titles are listed. */
IF (SELECT COUNT(*) FROM dbo.fn_BaoCao_TanSuat('2026-07-01', '2026-09-30')) <> 15
   OR (SELECT SUM(SOLUOTMUON) FROM dbo.fn_BaoCao_TanSuat('2026-07-01', '2026-09-30')) <> 8
BEGIN
    ;THROW 50211, 'The period book-frequency report is incorrect.', 1;
END;

/* 2026 stock review: 18 copies, including damaged S0006. */
IF (SELECT COUNT(*) FROM dbo.fn_BaoCao_SachCanXemXet('2026-01-01', '2026-12-31')) <> 18
   OR NOT EXISTS
   (
       SELECT 1 FROM dbo.fn_BaoCao_SachCanXemXet('2026-01-01', '2026-12-31')
       WHERE MASACH = 'S0006' AND LYDO = N'Hư hỏng'
   )
BEGIN
    ;THROW 50212, 'The stock-review report is incorrect.', 1;
END;

DECLARE @Summary TABLE
(
    KY NVARCHAR(20), TUNGAY DATE, DENNGAY DATE, NGAYCHOT DATE,
    SOPHIEUMUON INT, SOLUOTMUON INT, SODOCGIAMUON INT, SOLUOTTRA INT,
    SOLUOTTRATRE INT, TIENPHATTRATRE BIGINT, SOSACHQUAHAN_CUOIKY INT,
    SODOCGIAQUAHAN_CUOIKY INT, TIENPHATQUAHAN_CUOIKY BIGINT
);

INSERT INTO @Summary EXEC dbo.sp_ThongKe_TheoKy @Nam = 2026, @Quy = 3;

IF NOT EXISTS
(
    SELECT 1 FROM @Summary
    WHERE TUNGAY = '2026-07-01' AND DENNGAY = '2026-09-30'
      AND SOPHIEUMUON = 7 AND SOLUOTMUON = 8 AND SODOCGIAMUON = 7
      AND SOLUOTTRA = 7 AND SOLUOTTRATRE = 1 AND TIENPHATTRATRE = 4000
      AND SOSACHQUAHAN_CUOIKY = 0
)
BEGIN
    ;THROW 50213, 'The Q3 2026 period summary is incorrect.', 1;
END;

BEGIN TRY
    EXEC dbo.sp_ThongKe_TheoKy @Nam = 2026, @Thang = 1, @Quy = 1;
    ;THROW 50214, 'The period summary accepted both a month and a quarter.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 50301 THROW;
END CATCH;

SELECT N'PASS' AS Result, N'Reports and statistics' AS TestName;
GO

/* Server-side Reader/Book procedures (08_server_side_crud.sql). Rolled back. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Ids TABLE (MADG BIGINT);
DECLARE @NewMADG BIGINT, @MATL CHAR(5), @MANGONNGU INT, @MANGANTU INT;

BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO @Ids EXEC dbo.sp_DocGia_Them
        @HODG = N'Smoke', @TENDG = N'Test', @EMAILDG = N'smoke.crud@example.com',
        @SOCMND = '999000111222', @GIOITINH = 1, @NGAYSINH = '2000-01-01';
    SELECT @NewMADG = MADG FROM @Ids;
    IF @NewMADG IS NULL
        THROW 50220, 'sp_DocGia_Them did not return the new MADG.', 1;

    EXEC dbo.sp_DocGia_CapNhat @MADG = @NewMADG, @HODG = N'Smoke', @TENDG = N'Updated',
        @EMAILDG = N'smoke.crud@example.com', @SOCMND = '999000111222', @GIOITINH = 0;
    IF NOT EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE MADG = @NewMADG AND TENDG = N'Updated' AND GIOITINH = 0)
        THROW 50221, 'sp_DocGia_CapNhat did not update the reader.', 1;

    EXEC dbo.sp_DocGia_GiaHan @MADG = @NewMADG, @SoThang = 6;
    EXEC dbo.sp_DocGia_DoiTrangThai @MADG = @NewMADG, @HoatDong = 0;
    IF EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE MADG = @NewMADG AND HOATDONG = 1)
        THROW 50222, 'sp_DocGia_DoiTrangThai did not lock the card.', 1;

    DECLARE @ReaderDeleteState TABLE (
        MADG BIGINT, HODG NVARCHAR(50), TENDG NVARCHAR(12), EMAILDG NVARCHAR(50),
        SOCMND VARCHAR(12), GIOITINH BIT, NgaySinh VARCHAR(10), DIACHI NVARCHAR(100),
        DIENTHOAI VARCHAR(11), NgayLamThe VARCHAR(10), NgayHetHan VARCHAR(10), HOATDONG BIT,
        CoTheXoa BIT, LyDoKhongDuocXoa NVARCHAR(200)
    );
    INSERT INTO @ReaderDeleteState
        EXEC dbo.sp_DocGia_DanhSach @Keyword = N'999000111222';
    IF NOT EXISTS (
        SELECT 1 FROM @ReaderDeleteState
        WHERE MADG = @NewMADG AND CoTheXoa = 1 AND LyDoKhongDuocXoa = N''
    )
        THROW 50229, 'Reader delete eligibility was not returned correctly.', 1;

    DECLARE @Active TABLE (MADG BIGINT, HODG NVARCHAR(50), TENDG NVARCHAR(12), SOCMND VARCHAR(12));
    INSERT INTO @Active EXEC dbo.sp_DocGia_DanhSachHoatDong;
    IF EXISTS (SELECT 1 FROM @Active WHERE MADG = @NewMADG)
       OR EXISTS (SELECT 1 FROM @Active AS a JOIN dbo.DOCGIA AS d ON d.MADG = a.MADG WHERE d.HOATDONG = 0)
        THROW 50223, 'sp_DocGia_DanhSachHoatDong returned a locked card.', 1;

    EXEC dbo.sp_DocGia_Xoa @MADG = @NewMADG;
    IF EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE MADG = @NewMADG)
        THROW 50224, 'sp_DocGia_Xoa did not delete the reader.', 1;

    SELECT TOP (1) @MATL = MATL FROM dbo.THELOAI;
    SELECT TOP (1) @MANGONNGU = MANGONNGU FROM dbo.NGONNGU;
    SELECT TOP (1) @MANGANTU = MANGANTU FROM dbo.NGANTU;

    EXEC dbo.sp_DauSach_Them @ISBN = 'SMK0000001', @TENSACH = N'Smoke title',
        @GIA = 1000, @MANGONNGU = @MANGONNGU, @MATL = @MATL;

    DECLARE @TitleDeleteState TABLE (
        ISBN VARCHAR(20), TENSACH NVARCHAR(100), THELOAI NVARCHAR(50), HOTENTG NVARCHAR(MAX),
        NGONNGU NVARCHAR(50), SOTRANG INT, GIA BIGINT, GiaBia BIGINT, NHAXB NVARCHAR(100),
        LANXUATBAN INT, TongBanSao INT, BanSaoKhaDung INT,
        CoTheXoa BIT, LyDoKhongDuocXoa NVARCHAR(200)
    );
    INSERT INTO @TitleDeleteState
        EXEC dbo.sp_DauSach_DanhSach @Keyword = N'SMK0000001';
    IF NOT EXISTS (
        SELECT 1 FROM @TitleDeleteState WHERE ISBN = 'SMK0000001' AND CoTheXoa = 1
    )
        THROW 50230, 'A title without copies was not marked deletable.', 1;

    EXEC dbo.sp_DauSach_CapNhat @ISBN = 'SMK0000001', @TENSACH = N'Smoke title 2', @GIA = 2000;
    EXEC dbo.sp_Sach_Them @MASACH = 'SMK001', @ISBN = 'SMK0000001', @MANGANTU = @MANGANTU;
    EXEC dbo.sp_Sach_CapNhatTinhTrang @MASACH = 'SMK001', @TINHTRANG = 0;
    IF NOT EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH = 'SMK001' AND TINHTRANG = 0)
       OR NOT EXISTS (SELECT 1 FROM dbo.ISBN WHERE ISBN = 'SMK0000001' AND TENSACH = N'Smoke title 2')
        THROW 50225, 'Book add/update procedures did not write as expected.', 1;

    DELETE FROM @TitleDeleteState;
    INSERT INTO @TitleDeleteState
        EXEC dbo.sp_DauSach_DanhSach @Keyword = N'SMK0000001';
    IF NOT EXISTS (
        SELECT 1 FROM @TitleDeleteState
        WHERE ISBN = 'SMK0000001' AND CoTheXoa = 0 AND LyDoKhongDuocXoa <> N''
    )
        THROW 50231, 'A title with a physical copy was not protected from deletion.', 1;

    DECLARE @CopyDeleteState TABLE (
        MASACH VARCHAR(20), ISBN VARCHAR(20), TENSACH NVARCHAR(100),
        THELOAI NVARCHAR(50), TheLoaiAlias NVARCHAR(50), HOTENTG NVARCHAR(MAX),
        HoTenTGAlias NVARCHAR(MAX), TINHTRANG BIT, CHOMUON BIT, MANGANTU INT,
        ViTri NVARCHAR(200), GiaBia BIGINT, CoTheXoa BIT, LyDoKhongDuocXoa NVARCHAR(200)
    );
    INSERT INTO @CopyDeleteState
        EXEC dbo.sp_Sach_DanhSach @Keyword = N'SMK001';
    IF NOT EXISTS (
        SELECT 1 FROM @CopyDeleteState
        WHERE MASACH = 'SMK001' AND CoTheXoa = 1 AND LyDoKhongDuocXoa = N''
    )
        THROW 50232, 'A copy without loan history was not marked deletable.', 1;

    EXEC dbo.sp_Sach_Huy @MASACH = 'SMK001';
    EXEC dbo.sp_DauSach_Xoa @ISBN = 'SMK0000001';
    IF EXISTS (SELECT 1 FROM dbo.ISBN WHERE ISBN = 'SMK0000001')
        THROW 50226, 'sp_DauSach_Xoa did not delete the title.', 1;

    ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

/* Business-rule THROWs reach the caller with their 5xxxx number. */
BEGIN TRY
    EXEC dbo.sp_DocGia_Xoa @MADG = -1;
    ;THROW 50227, 'sp_DocGia_Xoa accepted a missing reader.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 52106 THROW;
END CATCH;

BEGIN TRY
    EXEC dbo.sp_Sach_Huy @MASACH = 'NO_SUCH';
    ;THROW 50228, 'sp_Sach_Huy accepted a missing copy.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 53105 THROW;
END CATCH;

SELECT N'PASS' AS Result, N'Server-side Reader/Book procedures' AS TestName;
SELECT N'ALL_DATABASE_SMOKE_TESTS_PASSED' AS Result;
GO
