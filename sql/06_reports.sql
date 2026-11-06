/*
    Library Management System - Reports & Statistics

    Spec section "Báo cáo thống kê": monthly or quarterly reports of
    - readers with overdue books (độc giả mượn sách quá hạn), and
    - book usage frequency (tần suất sử dụng sách).
    The yearly stock review (damaged books and books nobody borrows) is
    covered by fn_BaoCao_SachCanXemXet.

    Business rules reused from 01_create_tables.sql: 30-day loan period and
    500 VND per overdue day. Overdue days count up to the report date.

    Date parameters are inclusive calendar dates (DATE). Loan dates are
    SMALLDATETIME, so "on or before @Ngay" is written as "< @Ngay + 1 day".

    Run after 03_login_and_permissions.sql (the EXECUTE grant needs the
    application role). Safe to re-run.
*/

:on error exit

USE [LibraryManagement];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/*
    R1 - Readers with overdue books as of @NgayBaoCao.
    A loan line is overdue when it was borrowed on or before the report date,
    had not been returned by the end of that date, and its due date
    (NGAYMUON + 30 days) is before the report date.
*/
CREATE OR ALTER FUNCTION dbo.fn_BaoCao_QuaHan (@NgayBaoCao DATE)
RETURNS TABLE
AS
RETURN
(
    SELECT
        reader.MADG,
        reader.HODG + N' ' + reader.TENDG AS HOTENDG,
        reader.EMAILDG,
        reader.DIENTHOAI,
        loan.MAPHIEU,
        detail.MASACH,
        title.ISBN,
        title.TENSACH,
        loan.NGAYMUON,
        DATEADD(DAY, 30, loan.NGAYMUON) AS NGAYHENTRA,
        DATEDIFF(DAY, DATEADD(DAY, 30, loan.NGAYMUON), @NgayBaoCao) AS SONGAYQUAHAN,
        CONVERT(BIGINT, 500)
            * DATEDIFF(DAY, DATEADD(DAY, 30, loan.NGAYMUON), @NgayBaoCao) AS TIENPHAT
    FROM dbo.PHIEUMUON AS loan
    INNER JOIN dbo.CT_PHIEUMUON AS detail ON detail.MAPHIEU = loan.MAPHIEU
    INNER JOIN dbo.DOCGIA AS reader ON reader.MADG = loan.MADG
    INNER JOIN dbo.SACH AS book ON book.MASACH = detail.MASACH
    INNER JOIN dbo.ISBN AS title ON title.ISBN = book.ISBN
    WHERE loan.NGAYMUON < DATEADD(DAY, 1, CONVERT(DATETIME, @NgayBaoCao))
      AND
      (
          detail.TRA = 0
          OR detail.NGAYTRA >= DATEADD(DAY, 1, CONVERT(DATETIME, @NgayBaoCao))
      )
      AND DATEDIFF(DAY, DATEADD(DAY, 30, loan.NGAYMUON), @NgayBaoCao) > 0
);
GO

/*
    R2 - Book usage frequency for loans made between @TuNgay and @DenNgay.
    Every title is listed, including titles nobody borrowed in the period.
*/
CREATE OR ALTER FUNCTION dbo.fn_BaoCao_TanSuat (@TuNgay DATE, @DenNgay DATE)
RETURNS TABLE
AS
RETURN
(
    WITH PeriodLoans AS
    (
        SELECT book.ISBN, loan.MADG
        FROM dbo.PHIEUMUON AS loan
        INNER JOIN dbo.CT_PHIEUMUON AS detail ON detail.MAPHIEU = loan.MAPHIEU
        INNER JOIN dbo.SACH AS book ON book.MASACH = detail.MASACH
        WHERE loan.NGAYMUON >= @TuNgay
          AND loan.NGAYMUON < DATEADD(DAY, 1, CONVERT(DATETIME, @DenNgay))
    ),
    LoanCounts AS
    (
        SELECT ISBN, COUNT(*) AS SOLUOTMUON, COUNT(DISTINCT MADG) AS SODOCGIA
        FROM PeriodLoans
        GROUP BY ISBN
    ),
    CopyCounts AS
    (
        SELECT ISBN, COUNT(*) AS SOBANSAO
        FROM dbo.SACH
        GROUP BY ISBN
    )
    SELECT
        DENSE_RANK() OVER (ORDER BY COALESCE(counts.SOLUOTMUON, 0) DESC) AS XEPHANG,
        title.ISBN,
        title.TENSACH,
        category.THELOAI,
        COALESCE(copies.SOBANSAO, 0) AS SOBANSAO,
        COALESCE(counts.SOLUOTMUON, 0) AS SOLUOTMUON,
        COALESCE(counts.SODOCGIA, 0) AS SODOCGIA
    FROM dbo.ISBN AS title
    INNER JOIN dbo.THELOAI AS category ON category.MATL = title.MATL
    LEFT JOIN LoanCounts AS counts ON counts.ISBN = title.ISBN
    LEFT JOIN CopyCounts AS copies ON copies.ISBN = title.ISBN
);
GO

/*
    R3 - Stock review: physical copies that are damaged, or that nobody
    borrowed between @TuNgay and @DenNgay and are not currently on loan.
    This is the candidate list the spec's yearly inspection produces before
    the management board decides what to discard.
*/
CREATE OR ALTER FUNCTION dbo.fn_BaoCao_SachCanXemXet (@TuNgay DATE, @DenNgay DATE)
RETURNS TABLE
AS
RETURN
(
    WITH LoanHistory AS
    (
        SELECT
            detail.MASACH,
            MAX(loan.NGAYMUON) AS LANMUONCUOI,
            SUM
            (
                CASE
                    WHEN loan.NGAYMUON >= @TuNgay
                     AND loan.NGAYMUON < DATEADD(DAY, 1, CONVERT(DATETIME, @DenNgay))
                    THEN 1 ELSE 0
                END
            ) AS SOLUOTMUON_TRONGKY
        FROM dbo.CT_PHIEUMUON AS detail
        INNER JOIN dbo.PHIEUMUON AS loan ON loan.MAPHIEU = detail.MAPHIEU
        GROUP BY detail.MASACH
    )
    SELECT
        book.MASACH,
        title.ISBN,
        title.TENSACH,
        shelf.KE,
        shelf.MOTA AS VITRI,
        history.LANMUONCUOI,
        CASE
            WHEN book.TINHTRANG = 0 THEN N'Hư hỏng'
            ELSE N'Không có độc giả mượn'
        END AS LYDO
    FROM dbo.SACH AS book
    INNER JOIN dbo.ISBN AS title ON title.ISBN = book.ISBN
    INNER JOIN dbo.NGANTU AS shelf ON shelf.MANGANTU = book.MANGANTU
    LEFT JOIN LoanHistory AS history ON history.MASACH = book.MASACH
    WHERE book.TINHTRANG = 0
       OR (book.CHOMUON = 0 AND COALESCE(history.SOLUOTMUON_TRONGKY, 0) = 0)
);
GO

/*
    R4 - One-row summary for a year, a quarter, or a month.
      EXEC dbo.sp_ThongKe_TheoKy @Nam = 2026;              -- whole year
      EXEC dbo.sp_ThongKe_TheoKy @Nam = 2026, @Quy = 3;    -- Q3
      EXEC dbo.sp_ThongKe_TheoKy @Nam = 2026, @Thang = 10; -- October
    Overdue figures are taken at the end of the period, or today if the
    period has not ended yet.
*/
CREATE OR ALTER PROCEDURE dbo.sp_ThongKe_TheoKy
    @Nam   INT,
    @Thang INT = NULL,
    @Quy   INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @Nam IS NULL OR @Nam NOT BETWEEN 1900 AND 2078
        THROW 50300, N'Năm không hợp lệ (1900-2078).', 1;
    IF @Thang IS NOT NULL AND @Quy IS NOT NULL
        THROW 50301, N'Chỉ chọn tháng hoặc quý, không chọn cả hai.', 1;
    IF @Thang IS NOT NULL AND @Thang NOT BETWEEN 1 AND 12
        THROW 50302, N'Tháng phải từ 1 đến 12.', 1;
    IF @Quy IS NOT NULL AND @Quy NOT BETWEEN 1 AND 4
        THROW 50303, N'Quý phải từ 1 đến 4.', 1;

    DECLARE @TuNgay DATE =
        CASE
            WHEN @Thang IS NOT NULL THEN DATEFROMPARTS(@Nam, @Thang, 1)
            WHEN @Quy IS NOT NULL THEN DATEFROMPARTS(@Nam, (@Quy - 1) * 3 + 1, 1)
            ELSE DATEFROMPARTS(@Nam, 1, 1)
        END;
    DECLARE @DenNgay DATE =
        CASE
            WHEN @Thang IS NOT NULL THEN EOMONTH(@TuNgay)
            WHEN @Quy IS NOT NULL THEN EOMONTH(@TuNgay, 2)
            ELSE DATEFROMPARTS(@Nam, 12, 31)
        END;
    DECLARE @HomNay DATE = CONVERT(DATE, GETDATE());
    DECLARE @NgayChot DATE = CASE WHEN @DenNgay > @HomNay THEN @HomNay ELSE @DenNgay END;
    DECLARE @KetThuc DATETIME = DATEADD(DAY, 1, CONVERT(DATETIME, @DenNgay));

    SELECT
        CASE
            WHEN @Thang IS NOT NULL
                THEN N'Tháng ' + CONVERT(NVARCHAR(2), @Thang) + N'/' + CONVERT(NVARCHAR(4), @Nam)
            WHEN @Quy IS NOT NULL
                THEN N'Quý ' + CONVERT(NVARCHAR(1), @Quy) + N'/' + CONVERT(NVARCHAR(4), @Nam)
            ELSE N'Năm ' + CONVERT(NVARCHAR(4), @Nam)
        END AS KY,
        @TuNgay AS TUNGAY,
        @DenNgay AS DENNGAY,
        @NgayChot AS NGAYCHOT,
        (
            SELECT COUNT(*) FROM dbo.PHIEUMUON
            WHERE NGAYMUON >= @TuNgay AND NGAYMUON < @KetThuc
        ) AS SOPHIEUMUON,
        (
            SELECT COUNT(*)
            FROM dbo.PHIEUMUON AS loan
            INNER JOIN dbo.CT_PHIEUMUON AS detail ON detail.MAPHIEU = loan.MAPHIEU
            WHERE loan.NGAYMUON >= @TuNgay AND loan.NGAYMUON < @KetThuc
        ) AS SOLUOTMUON,
        (
            SELECT COUNT(DISTINCT MADG) FROM dbo.PHIEUMUON
            WHERE NGAYMUON >= @TuNgay AND NGAYMUON < @KetThuc
        ) AS SODOCGIAMUON,
        (
            SELECT COUNT(*) FROM dbo.CT_PHIEUMUON
            WHERE TRA = 1 AND NGAYTRA >= @TuNgay AND NGAYTRA < @KetThuc
        ) AS SOLUOTTRA,
        (
            SELECT COUNT(*) FROM dbo.v_CHITIET_MUONTRA
            WHERE TRA = 1 AND NGAYTRA >= @TuNgay AND NGAYTRA < @KetThuc
              AND SONGAYQUAHAN > 0
        ) AS SOLUOTTRATRE,
        (
            SELECT COALESCE(SUM(TIENPHATQUAHAN), 0) FROM dbo.v_CHITIET_MUONTRA
            WHERE TRA = 1 AND NGAYTRA >= @TuNgay AND NGAYTRA < @KetThuc
              AND SONGAYQUAHAN > 0
        ) AS TIENPHATTRATRE,
        (
            SELECT COUNT(*) FROM dbo.fn_BaoCao_QuaHan(@NgayChot)
        ) AS SOSACHQUAHAN_CUOIKY,
        (
            SELECT COUNT(DISTINCT MADG) FROM dbo.fn_BaoCao_QuaHan(@NgayChot)
        ) AS SODOCGIAQUAHAN_CUOIKY,
        (
            SELECT COALESCE(SUM(TIENPHAT), 0) FROM dbo.fn_BaoCao_QuaHan(@NgayChot)
        ) AS TIENPHATQUAHAN_CUOIKY;
END;
GO

/*
    library_app_role and QUANLY already have SELECT on schema dbo (covers the
    functions); QUANLY also has EXECUTE. THUTHU (librarian) only has
    per-object grants, so it needs each report object granted explicitly.
*/
IF DATABASE_PRINCIPAL_ID(N'library_app_role') IS NOT NULL
BEGIN
    GRANT EXECUTE ON OBJECT::dbo.sp_ThongKe_TheoKy TO [library_app_role];
END;

IF DATABASE_PRINCIPAL_ID(N'THUTHU') IS NOT NULL
BEGIN
    GRANT SELECT ON OBJECT::dbo.fn_BaoCao_QuaHan TO [THUTHU];
    GRANT SELECT ON OBJECT::dbo.fn_BaoCao_TanSuat TO [THUTHU];
    GRANT SELECT ON OBJECT::dbo.fn_BaoCao_SachCanXemXet TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_ThongKe_TheoKy TO [THUTHU];
END;
GO
