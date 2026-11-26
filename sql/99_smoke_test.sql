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
    EXEC dbo.sp_DauSach_CapNhat @ISBN = 'SMK0000001', @TENSACH = N'Smoke title 2', @GIA = 2000;
    EXEC dbo.sp_Sach_Them @MASACH = 'SMK001', @ISBN = 'SMK0000001', @MANGANTU = @MANGANTU;
    EXEC dbo.sp_Sach_CapNhatTinhTrang @MASACH = 'SMK001', @TINHTRANG = 0;
    IF NOT EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH = 'SMK001' AND TINHTRANG = 0)
       OR NOT EXISTS (SELECT 1 FROM dbo.ISBN WHERE ISBN = 'SMK0000001' AND TENSACH = N'Smoke title 2')
        THROW 50225, 'Book add/update procedures did not write as expected.', 1;

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
GO

/* Borrow/return transactions (09_borrowing_transactions.sql).
   Test rows are picked from the current data so the test does not depend on
   which copies are on loan today. The happy path runs inside an outer
   transaction that is rolled back; error paths run on their own and must
   leave no trace (each procedure rolls back its own work). */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Manv INT, @Reader BIGINT, @Isbn CHAR(10), @Gia BIGINT;
DECLARE @B1 VARCHAR(10), @B2 VARCHAR(10), @B3 VARCHAR(10), @List NVARCHAR(500);
DECLARE @MaPhieu BIGINT, @LoansBefore INT, @Err INT;
DECLARE @NewLoan TABLE (MAPHIEU BIGINT);
DECLARE @OneFine TABLE (
    MAPHIEU BIGINT, MASACH VARCHAR(10), TENSACH NVARCHAR(100), GiaBia BIGINT,
    SoNgayDaMuon INT, SoNgayTre INT, TienPhatTre BIGINT, TienMatSach BIGINT,
    TienPhatHong BIGINT, TongPhat BIGINT);
DECLARE @BatchFine TABLE (
    MAPHIEU BIGINT, ISBN CHAR(10), SoCuonTra INT, TienPhatTre BIGINT,
    TienMatSach BIGINT, TienPhatHong BIGINT, TongPhat BIGINT);
DECLARE @Free TABLE (MASACH VARCHAR(10) PRIMARY KEY, ISBN CHAR(10));

SELECT TOP (1) @Manv = MANV FROM dbo.NHANVIEN ORDER BY MANV;

/* A reader whose card is valid and who holds no book. */
SELECT TOP (1) @Reader = dg.MADG
FROM dbo.DOCGIA AS dg
WHERE dg.HOATDONG = 1 AND dg.NGAYHETHAN >= GETDATE()
  AND NOT EXISTS (
      SELECT 1 FROM dbo.CT_PHIEUMUON AS ct
      JOIN dbo.PHIEUMUON AS pm ON pm.MAPHIEU = ct.MAPHIEU
      JOIN dbo.DOCGIA AS same ON same.MADG = pm.MADG
      WHERE same.SOCMND = dg.SOCMND AND ct.TRA = 0)
ORDER BY dg.MADG;

INSERT INTO @Free (MASACH, ISBN)
SELECT MASACH, ISBN FROM dbo.SACH WHERE CHOMUON = 0 AND TINHTRANG = 1;

/* Two free copies of one title (for the by-ISBN return) and one other copy. */
SELECT TOP (1) @Isbn = ISBN FROM @Free GROUP BY ISBN HAVING COUNT(*) >= 2 ORDER BY ISBN;
SELECT @B1 = MIN(MASACH), @B2 = MAX(MASACH) FROM (
    SELECT TOP (2) MASACH FROM @Free WHERE ISBN = @Isbn ORDER BY MASACH) AS two;
SELECT TOP (1) @B3 = MASACH FROM @Free WHERE ISBN <> @Isbn ORDER BY MASACH;
SELECT @Gia = ISNULL(GIA, 0) FROM dbo.ISBN WHERE ISBN = @Isbn;

IF @Manv IS NULL OR @Reader IS NULL OR @B1 IS NULL OR @B3 IS NULL
    THROW 50230, 'Sample data lacks a free reader or free copies for the borrowing tests.', 1;

SET @List = CONCAT(@B1, N',', @B2, N',', @B3);

BEGIN TRY
    BEGIN TRANSACTION;

    /* Lend three copies in one call. */
    INSERT INTO @NewLoan EXEC dbo.sp_PhieuMuon_Tao
        @MADG = @Reader, @MANV = @Manv, @HinhThuc = 1, @DanhSachMaSach = @List;
    SELECT @MaPhieu = MAPHIEU FROM @NewLoan;

    IF @MaPhieu IS NULL
       OR (SELECT COUNT(*) FROM dbo.CT_PHIEUMUON WHERE MAPHIEU = @MaPhieu AND TRA = 0) <> 3
       OR EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH IN (@B1, @B2, @B3) AND CHOMUON <> 1)
        THROW 50231, 'sp_PhieuMuon_Tao did not write the loan and lock the copies.', 1;

    /* Return @B3 damaged: 50% fine, copy becomes unusable. */
    INSERT INTO @OneFine EXEC dbo.sp_PhieuMuon_XacNhanTra
        @MAPHIEU = @MaPhieu, @MASACH = @B3, @MANVNS = @Manv, @TinhTrangTra = 0, @BiMat = 0;

    IF NOT EXISTS (
            SELECT 1 FROM @OneFine AS f
            JOIN dbo.SACH AS s ON s.MASACH = f.MASACH
            JOIN dbo.ISBN AS i ON i.ISBN = s.ISBN
            WHERE f.TienPhatHong = ISNULL(i.GIA, 0) / 2 AND f.TienMatSach = 0 AND f.TienPhatTre = 0
              AND s.CHOMUON = 0 AND s.TINHTRANG = 0)
       OR NOT EXISTS (SELECT 1 FROM dbo.CT_PHIEUMUON
                      WHERE MAPHIEU = @MaPhieu AND MASACH = @B3 AND TRA = 1 AND MANVNS = @Manv)
        THROW 50232, 'sp_PhieuMuon_XacNhanTra did not return the copy with a 50% damage fine.', 1;

    ROLLBACK TRANSACTION;
    SELECT N'PASS' AS Result, N'Borrow transaction and single return' AS TestName;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

/* By-ISBN return of two lost copies: 100% of the cover price each. */
BEGIN TRY
    BEGIN TRANSACTION;
    DELETE FROM @NewLoan;

    INSERT INTO @NewLoan EXEC dbo.sp_PhieuMuon_Tao
        @MADG = @Reader, @MANV = @Manv, @HinhThuc = 1, @DanhSachMaSach = @List;
    SELECT @MaPhieu = MAPHIEU FROM @NewLoan;

    INSERT INTO @BatchFine EXEC dbo.sp_PhieuMuon_TraTheoISBN
        @MAPHIEU = @MaPhieu, @ISBN = @Isbn, @SoLuong = 2, @MANVNS = @Manv,
        @TinhTrangTra = 0, @BiMat = 1;

    IF NOT EXISTS (SELECT 1 FROM @BatchFine
                   WHERE SoCuonTra = 2 AND TienMatSach = 2 * @Gia AND TienPhatHong = 0
                     AND TongPhat = 2 * @Gia)
       OR EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH IN (@B1, @B2) AND (CHOMUON <> 0 OR TINHTRANG <> 0))
       OR NOT EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH = @B3 AND CHOMUON = 1)
        THROW 50234, 'sp_PhieuMuon_TraTheoISBN did not return the two lost copies correctly.', 1;

    ROLLBACK TRANSACTION;
    SELECT N'PASS' AS Result, N'Return by ISBN (lost copies)' AS TestName;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

/* Rule violations: each THROWs its number and writes nothing. */
SELECT @LoansBefore = COUNT(*) FROM dbo.PHIEUMUON;

BEGIN TRY
    EXEC dbo.sp_PhieuMuon_Tao @MADG = @Reader, @MANV = @Manv, @HinhThuc = 1,
        @DanhSachMaSach = N'S0001,S0002,S0003,S0004';
    THROW 50235, 'Four copies in one loan were accepted.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 54101 THROW;
END CATCH;

BEGIN TRY
    SET @List = CONCAT(@B1, N',', @B1);
    EXEC dbo.sp_PhieuMuon_Tao @MADG = @Reader, @MANV = @Manv, @HinhThuc = 1, @DanhSachMaSach = @List;
    THROW 50236, 'A duplicated copy code was accepted.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 54106 THROW;
END CATCH;

/* Rollback: one free copy plus one that is unusable or on loan. The free copy
   must stay free and no PHIEUMUON row may remain. */
BEGIN TRY
    SELECT TOP (1) @List = CONCAT(@B1, N',', MASACH)
    FROM dbo.SACH WHERE CHOMUON = 1 OR TINHTRANG = 0 ORDER BY MASACH;
    EXEC dbo.sp_PhieuMuon_Tao @MADG = @Reader, @MANV = @Manv, @HinhThuc = 1, @DanhSachMaSach = @List;
    THROW 50237, 'An unavailable copy was lent.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 54105 THROW;
END CATCH;

IF (SELECT COUNT(*) FROM dbo.PHIEUMUON) <> @LoansBefore
   OR EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH = @B1 AND CHOMUON <> 0)
    THROW 50238, 'A failed loan left data behind (transaction was not rolled back).', 1;

BEGIN TRY
    EXEC dbo.sp_PhieuMuon_Tao @MADG = -1, @MANV = @Manv, @HinhThuc = 1, @DanhSachMaSach = @B1;
    THROW 50239, 'A missing reader card was accepted.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 54102 THROW;
END CATCH;

/* Limit: a reader who holds N books cannot take (4 - N) more. */
DECLARE @Holder BIGINT, @Held INT;
SELECT TOP (1) @Holder = dg.MADG, @Held = COUNT(*)
FROM dbo.DOCGIA AS dg
JOIN dbo.PHIEUMUON AS pm ON pm.MADG = dg.MADG
JOIN dbo.CT_PHIEUMUON AS ct ON ct.MAPHIEU = pm.MAPHIEU AND ct.TRA = 0
WHERE dg.HOATDONG = 1 AND dg.NGAYHETHAN >= GETDATE()
GROUP BY dg.MADG
ORDER BY dg.MADG;

IF @Holder IS NOT NULL
BEGIN
    SELECT @List = STRING_AGG(MASACH, ',')
    FROM (SELECT TOP (4 - @Held) MASACH FROM @Free ORDER BY MASACH) AS extra;
    BEGIN TRY
        EXEC dbo.sp_PhieuMuon_Tao @MADG = @Holder, @MANV = @Manv, @HinhThuc = 1, @DanhSachMaSach = @List;
        THROW 50241, 'The three-book limit was not enforced.', 1;
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() <> 54104 THROW;
    END CATCH;
END;

/* A loan line that was already returned cannot be returned again. */
DECLARE @ReturnedLoan BIGINT, @ReturnedBook VARCHAR(10);
SELECT TOP (1) @ReturnedLoan = MAPHIEU, @ReturnedBook = MASACH
FROM dbo.CT_PHIEUMUON WHERE TRA = 1 ORDER BY MAPHIEU;

BEGIN TRY
    EXEC dbo.sp_PhieuMuon_XacNhanTra @MAPHIEU = @ReturnedLoan, @MASACH = @ReturnedBook, @MANVNS = @Manv;
    THROW 50233, 'A copy was returned twice.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 54111 THROW;
END CATCH;

BEGIN TRY
    EXEC dbo.sp_PhieuMuon_TraTheoISBN @MAPHIEU = -1, @ISBN = @Isbn, @SoLuong = 1, @MANVNS = @Manv;
    THROW 50240, 'A by-ISBN return without open loan lines was accepted.', 1;
END TRY
BEGIN CATCH
    IF ERROR_NUMBER() <> 54114 THROW;
END CATCH;

SELECT N'PASS' AS Result, N'Borrow/return rule violations roll back' AS TestName;
SELECT N'ALL_DATABASE_SMOKE_TESTS_PASSED' AS Result;
GO
