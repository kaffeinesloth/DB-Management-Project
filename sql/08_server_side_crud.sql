/*
    Library Management System - Server-side processing for Readers and Books

    Lecturer rule: "Nguyên tắc xử lý tại Server". Every read and write on
    DOCGIA (readers), ISBN / TACGIA_SACH (book titles) and SACH (physical copies)
    goes through these stored procedures. The Python client only sends EXEC.

    Conventions
    - SET NOCOUNT ON, so the client never relies on @@ROWCOUNT. "Not found"
      and business rules are raised with THROW and a Vietnamese message:
        521xx = readers, 531xx = books.
    - Multi-statement writes run in BEGIN TRY / BEGIN TRANSACTION / COMMIT,
      with ROLLBACK + THROW in CATCH.
    - Foreign-key (547), duplicate-key (2601/2627) and truncation errors are
      re-thrown unchanged; the client maps them by native error number.
    - New identity values are returned by a final SELECT.

    Run after 03_login_and_permissions.sql (grants need the roles). Safe to re-run.
*/

:on error exit

USE [LibraryManagement];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ======================================================================
   READERS (DOCGIA)
   ====================================================================== */

/* List / search reader cards. No keyword -> newest @Top cards. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_DanhSach
    @Keyword NVARCHAR(100) = NULL,
    @Top     INT = 500
AS
BEGIN
    SET NOCOUNT ON;

    SET @Keyword = NULLIF(LTRIM(RTRIM(@Keyword)), N'');
    IF @Top IS NULL OR @Top < 1 SET @Top = 1;
    IF @Top > 1000 SET @Top = 1000;

    DECLARE @Pattern NVARCHAR(102) = N'%' + @Keyword + N'%';

    SELECT TOP (CASE WHEN @Keyword IS NULL THEN @Top ELSE 2147483647 END)
        MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
        CONVERT(VARCHAR(10), NGAYSINH, 103)   AS NgaySinh,
        DIACHI, DIENTHOAI,
        CONVERT(VARCHAR(10), NGAYLAMTHE, 103) AS NgayLamThe,
        CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHan,
        HOATDONG
    FROM dbo.DOCGIA
    WHERE @Keyword IS NULL
       OR TENDG LIKE @Pattern
       OR HODG LIKE @Pattern
       OR SOCMND LIKE @Pattern
       OR DIENTHOAI LIKE @Pattern
       OR EMAILDG LIKE @Pattern
       OR CAST(MADG AS VARCHAR(20)) LIKE @Pattern
    ORDER BY MADG DESC;
END;
GO

/* Active cards only, for the borrowing screen's reader picker. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_DanhSachHoatDong
AS
BEGIN
    SET NOCOUNT ON;

    SELECT MADG, HODG, TENDG, SOCMND
    FROM dbo.DOCGIA
    WHERE HOATDONG = 1
    ORDER BY MADG ASC;
END;
GO

/* One card with raw date values (used to fill the edit form). */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_ChiTiet
    @MADG BIGINT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
           NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
    FROM dbo.DOCGIA
    WHERE MADG = @MADG;
END;
GO

/* Duplicate check for the add form: identity number / email on another active card. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_KiemTraTrung
    @SOCMND      VARCHAR(20)   = NULL,
    @EMAILDG     NVARCHAR(100) = NULL,
    @ExcludeMADG BIGINT        = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SET @SOCMND = NULLIF(LTRIM(RTRIM(@SOCMND)), '');
    SET @EMAILDG = NULLIF(LTRIM(RTRIM(@EMAILDG)), N'');

    SELECT
        CAST(CASE WHEN @SOCMND IS NOT NULL AND EXISTS (
            SELECT 1 FROM dbo.DOCGIA
            WHERE SOCMND = @SOCMND AND HOATDONG = 1
              AND (@ExcludeMADG IS NULL OR MADG <> @ExcludeMADG)
        ) THEN 1 ELSE 0 END AS BIT) AS CmndTrung,
        CAST(CASE WHEN @EMAILDG IS NOT NULL AND EXISTS (
            SELECT 1 FROM dbo.DOCGIA
            WHERE EMAILDG = @EMAILDG AND HOATDONG = 1
              AND (@ExcludeMADG IS NULL OR MADG <> @ExcludeMADG)
        ) THEN 1 ELSE 0 END AS BIT) AS EmailTrung;
END;
GO

/* Issue a new reader card; returns the new MADG. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_Them
    @HODG       NVARCHAR(50),
    @TENDG      NVARCHAR(12),
    @EMAILDG    NVARCHAR(50)  = NULL,
    @SOCMND     VARCHAR(12),
    @GIOITINH   BIT           = 1,
    @NGAYSINH   SMALLDATETIME = NULL,
    @DIACHI     NVARCHAR(100) = NULL,
    @DIENTHOAI  VARCHAR(11)   = NULL,
    @NGAYLAMTHE SMALLDATETIME = NULL,
    @NGAYHETHAN SMALLDATETIME = NULL,
    @HOATDONG   BIT           = 1
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @HODG = NULLIF(LTRIM(RTRIM(@HODG)), N'');
    SET @TENDG = NULLIF(LTRIM(RTRIM(@TENDG)), N'');
    SET @SOCMND = NULLIF(LTRIM(RTRIM(@SOCMND)), '');
    SET @EMAILDG = NULLIF(LTRIM(RTRIM(@EMAILDG)), N'');
    SET @NGAYLAMTHE = ISNULL(@NGAYLAMTHE, GETDATE());
    SET @NGAYHETHAN = ISNULL(@NGAYHETHAN, DATEADD(MONTH, 12, @NGAYLAMTHE));
    SET @HOATDONG = ISNULL(@HOATDONG, 1);

    IF @HODG IS NULL OR @TENDG IS NULL
        THROW 52101, N'Vui lòng nhập đầy đủ họ đệm và tên độc giả!', 1;
    IF @SOCMND IS NULL
        THROW 52102, N'CMND/CCCD không được để trống!', 1;
    IF @NGAYHETHAN < @NGAYLAMTHE
        THROW 52103, N'Ngày hết hạn không được trước ngày làm thẻ!', 1;
    IF @HOATDONG = 1 AND EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE SOCMND = @SOCMND AND HOATDONG = 1)
        THROW 52104, N'CMND/CCCD này đã có một thẻ đang hoạt động!', 1;
    IF @EMAILDG IS NOT NULL AND EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE EMAILDG = @EMAILDG AND HOATDONG = 1)
        THROW 52105, N'Email này đã được đăng ký cho một thẻ đang hoạt động khác!', 1;

    INSERT INTO dbo.DOCGIA (
        HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
        NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
    )
    VALUES (
        @HODG, @TENDG, @EMAILDG, @SOCMND, @GIOITINH,
        @NGAYSINH, NULLIF(@DIACHI, N''), NULLIF(@DIENTHOAI, ''), @NGAYLAMTHE, @NGAYHETHAN, @HOATDONG
    );

    SELECT CAST(SCOPE_IDENTITY() AS BIGINT) AS MADG;
END;
GO

/*
    Edit an ACTIVE card's personal details. Card dates and status are not
    editable here. A corrected identity number is applied to every historical
    card of the same person, because SOCMND links replacement-card history for
    the person-level loan limit.
*/
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_CapNhat
    @MADG      BIGINT,
    @HODG      NVARCHAR(50),
    @TENDG     NVARCHAR(12),
    @EMAILDG   NVARCHAR(50)  = NULL,
    @SOCMND    VARCHAR(12),
    @GIOITINH  BIT           = 1,
    @NGAYSINH  SMALLDATETIME = NULL,
    @DIACHI    NVARCHAR(100) = NULL,
    @DIENTHOAI VARCHAR(11)   = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @HODG = NULLIF(LTRIM(RTRIM(@HODG)), N'');
    SET @TENDG = NULLIF(LTRIM(RTRIM(@TENDG)), N'');
    SET @SOCMND = NULLIF(LTRIM(RTRIM(@SOCMND)), '');
    SET @EMAILDG = NULLIF(LTRIM(RTRIM(@EMAILDG)), N'');

    IF @HODG IS NULL OR @TENDG IS NULL
        THROW 52101, N'Vui lòng nhập đầy đủ họ đệm và tên độc giả!', 1;
    IF @SOCMND IS NULL
        THROW 52102, N'CMND/CCCD không được để trống!', 1;

    DECLARE @OldSOCMND VARCHAR(12), @Active BIT;

    BEGIN TRY
        BEGIN TRANSACTION;

        SELECT @OldSOCMND = SOCMND, @Active = HOATDONG
        FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
        WHERE MADG = @MADG;

        IF @OldSOCMND IS NULL
            THROW 52106, N'Không tìm thấy thẻ độc giả; vui lòng làm mới danh sách!', 1;
        IF @Active = 0
            THROW 52107, N'Không thể sửa thẻ đã khóa vì đây là dữ liệu lịch sử. Hãy chọn thẻ đang hoạt động của độc giả.', 1;

        IF @SOCMND <> @OldSOCMND AND EXISTS (
            SELECT 1 FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
            WHERE SOCMND = @SOCMND
        )
            THROW 52108, N'CMND/CCCD mới đã thuộc về một độc giả khác!', 1;

        IF @EMAILDG IS NOT NULL AND EXISTS (
            SELECT 1 FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
            WHERE EMAILDG = @EMAILDG AND HOATDONG = 1 AND MADG <> @MADG
        )
            THROW 52105, N'Email này đã được đăng ký cho một thẻ đang hoạt động khác!', 1;

        IF @SOCMND <> @OldSOCMND
            UPDATE dbo.DOCGIA SET SOCMND = @SOCMND WHERE SOCMND = @OldSOCMND;

        UPDATE dbo.DOCGIA
        SET HODG = @HODG, TENDG = @TENDG, EMAILDG = @EMAILDG, SOCMND = @SOCMND,
            GIOITINH = @GIOITINH, NGAYSINH = @NGAYSINH,
            DIACHI = NULLIF(@DIACHI, N''), DIENTHOAI = NULLIF(@DIENTHOAI, '')
        WHERE MADG = @MADG AND HOATDONG = 1;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

/* Delete a card. A card with loan history is protected by FK_PHIEUMUON_DOCGIA (547). */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_Xoa
    @MADG BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF NOT EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE MADG = @MADG)
        THROW 52106, N'Không tìm thấy thẻ độc giả; vui lòng làm mới danh sách!', 1;

    DELETE FROM dbo.DOCGIA WHERE MADG = @MADG;
END;
GO

/* Extend a card by @SoThang months, counting from today if it has already expired. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_GiaHan
    @MADG    BIGINT,
    @SoThang INT = 12
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @SoThang IS NULL OR @SoThang < 1 OR @SoThang > 60
        THROW 52109, N'Số tháng gia hạn phải từ 1 đến 60!', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE MADG = @MADG)
        THROW 52106, N'Không tìm thấy thẻ độc giả; vui lòng làm mới danh sách!', 1;

    UPDATE dbo.DOCGIA
    SET NGAYHETHAN = DATEADD(MONTH, @SoThang,
        CASE WHEN NGAYHETHAN < GETDATE() THEN GETDATE() ELSE NGAYHETHAN END)
    WHERE MADG = @MADG;
END;
GO

/* Lock or unlock a card. UX_DOCGIA_SOCMND_ACTIVE blocks two active cards per person. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_DoiTrangThai
    @MADG     BIGINT,
    @HoatDong BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF NOT EXISTS (SELECT 1 FROM dbo.DOCGIA WHERE MADG = @MADG)
        THROW 52106, N'Không tìm thấy thẻ độc giả; vui lòng làm mới danh sách!', 1;

    UPDATE dbo.DOCGIA SET HOATDONG = ISNULL(@HoatDong, 0) WHERE MADG = @MADG;
END;
GO

/* Lost card: lock the old card and issue a new MADG for the same person, atomically. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_CapLaiThe
    @OldMADG BIGINT,
    @SoThang INT = 12
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @SoThang IS NULL OR @SoThang < 1 OR @SoThang > 60
        THROW 52110, N'Thời hạn thẻ cấp lại phải từ 1 đến 60 tháng!', 1;

    DECLARE @Active BIT, @Found BIT = 0;
    DECLARE @Now SMALLDATETIME = GETDATE();
    DECLARE @NewMADG BIGINT;

    BEGIN TRY
        BEGIN TRANSACTION;

        SELECT @Found = 1, @Active = HOATDONG
        FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
        WHERE MADG = @OldMADG;

        IF @Found = 0
            THROW 52106, N'Không tìm thấy thẻ độc giả; vui lòng làm mới danh sách!', 1;
        IF @Active = 0
            THROW 52111, N'Thẻ được chọn đã bị khóa nên không thể cấp lại lần nữa!', 1;

        UPDATE dbo.DOCGIA SET HOATDONG = 0 WHERE MADG = @OldMADG AND HOATDONG = 1;

        INSERT INTO dbo.DOCGIA (
            HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
            NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
        )
        SELECT HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
               NGAYSINH, DIACHI, DIENTHOAI, @Now, DATEADD(MONTH, @SoThang, @Now), 1
        FROM dbo.DOCGIA
        WHERE MADG = @OldMADG;

        SET @NewMADG = CAST(SCOPE_IDENTITY() AS BIGINT);
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @NewMADG AS MADG;
END;
GO

/* Can this card borrow? Counts unreturned books across all cards of the same person. */
CREATE OR ALTER PROCEDURE dbo.sp_DocGia_KiemTraMuonSach
    @MADG BIGINT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Active BIT, @Expired BIT, @ExpiryText VARCHAR(10), @SOCMND VARCHAR(12);
    DECLARE @DangGiu INT = 0;

    SELECT @Active = HOATDONG,
           @Expired = CASE WHEN NGAYHETHAN < GETDATE() THEN 1 ELSE 0 END,
           @ExpiryText = CONVERT(VARCHAR(10), NGAYHETHAN, 103),
           @SOCMND = SOCMND
    FROM dbo.DOCGIA
    WHERE MADG = @MADG;

    IF @SOCMND IS NULL
    BEGIN
        SELECT CAST(0 AS BIT) AS HopLe,
               N'Không tìm thấy thẻ độc giả mã ' + CAST(@MADG AS NVARCHAR(20)) + N'!' AS LyDo,
               0 AS DangGiu;
        RETURN;
    END;
    IF @Active = 0
    BEGIN
        SELECT CAST(0 AS BIT) AS HopLe, N'Thẻ độc giả đang bị KHÓA! Không thể mượn sách.' AS LyDo, 0 AS DangGiu;
        RETURN;
    END;
    IF @Expired = 1
    BEGIN
        SELECT CAST(0 AS BIT) AS HopLe,
               N'Thẻ độc giả đã HẾT HẠN từ ngày ' + @ExpiryText + N'! Vui lòng gia hạn thẻ.' AS LyDo,
               0 AS DangGiu;
        RETURN;
    END;

    SELECT @DangGiu = COUNT(*)
    FROM dbo.CT_PHIEUMUON AS ct
    INNER JOIN dbo.PHIEUMUON AS pm ON ct.MAPHIEU = pm.MAPHIEU
    INNER JOIN dbo.DOCGIA AS dg ON pm.MADG = dg.MADG
    WHERE dg.SOCMND = @SOCMND AND ct.TRA = 0;

    IF @DangGiu >= 3
        SELECT CAST(0 AS BIT) AS HopLe,
               N'Độc giả đang giữ ' + CAST(@DangGiu AS NVARCHAR(10))
               + N' cuốn chưa trả trên các thẻ đã cấp; đã đạt tối đa 3 cuốn!' AS LyDo,
               @DangGiu AS DangGiu;
    ELSE
        SELECT CAST(1 AS BIT) AS HopLe, N'Thẻ hợp lệ' AS LyDo, @DangGiu AS DangGiu;
END;
GO

/* ======================================================================
   BOOKS: lookups
   ====================================================================== */

CREATE OR ALTER PROCEDURE dbo.sp_DanhMuc_TheLoai
AS
BEGIN
    SET NOCOUNT ON;
    SELECT MATL, THELOAI FROM dbo.THELOAI ORDER BY THELOAI;
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_DanhMuc_NganTu
AS
BEGIN
    SET NOCOUNT ON;
    SELECT MANGANTU, KE, MOTA FROM dbo.NGANTU ORDER BY KE;
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_DanhMuc_TacGia
AS
BEGIN
    SET NOCOUNT ON;
    SELECT MATACGIA, HOTENTG FROM dbo.TACGIA ORDER BY HOTENTG;
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_DanhMuc_NgonNgu
AS
BEGIN
    SET NOCOUNT ON;
    SELECT MANGONNGU, NGONNGU FROM dbo.NGONNGU ORDER BY NGONNGU;
END;
GO

/* ======================================================================
   BOOKS: physical copies (SACH)
   ====================================================================== */

/* List / search physical copies with title, category, authors and shelf. */
CREATE OR ALTER PROCEDURE dbo.sp_Sach_DanhSach
    @Keyword NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Pattern NVARCHAR(102) = N'%' + ISNULL(LTRIM(RTRIM(@Keyword)), N'') + N'%';

    SELECT
        s.MASACH,
        s.ISBN,
        i.TENSACH,
        ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI,
        ISNULL(tl.THELOAI, N'Chưa phân loại') AS TheLoai,
        ISNULL(au.HOTENTG, N'Chưa rõ') AS HOTENTG,
        ISNULL(au.HOTENTG, N'Chưa rõ') AS HoTenTG,
        s.TINHTRANG,
        s.CHOMUON,
        s.MANGANTU,
        ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri,
        ISNULL(i.GIA, 0) AS GiaBia
    FROM dbo.SACH s
    INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
    LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
    LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
    OUTER APPLY (
        SELECT STRING_AGG(tg.HOTENTG, ', ') AS HOTENTG
        FROM dbo.TACGIA_SACH tgs
        JOIN dbo.TACGIA tg ON tgs.MATACGIA = tg.MATACGIA
        WHERE tgs.ISBN = s.ISBN
    ) AS au
    WHERE s.MASACH LIKE @Pattern
       OR i.TENSACH LIKE @Pattern
       OR s.ISBN LIKE @Pattern
       OR tl.THELOAI LIKE @Pattern
       OR EXISTS (
           SELECT 1 FROM dbo.TACGIA_SACH tgs2
           JOIN dbo.TACGIA tg2 ON tgs2.MATACGIA = tg2.MATACGIA
           WHERE tgs2.ISBN = s.ISBN AND tg2.HOTENTG LIKE @Pattern
       )
    ORDER BY s.MASACH ASC;
END;
GO

/* Copies available to lend (CHOMUON = 0 AND TINHTRANG = 1). */
CREATE OR ALTER PROCEDURE dbo.sp_Sach_SanSangChoMuon
AS
BEGIN
    SET NOCOUNT ON;

    SELECT s.MASACH, i.TENSACH, s.ISBN, ISNULL(i.GIA, 0) AS GiaBia,
           ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri
    FROM dbo.SACH s
    INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
    LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
    WHERE s.CHOMUON = 0 AND s.TINHTRANG = 1
    ORDER BY i.TENSACH ASC, s.MASACH ASC;
END;
GO

/* One copy's lending state; the client turns it into a message. */
CREATE OR ALTER PROCEDURE dbo.sp_Sach_KiemTraChoMuon
    @MASACH VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT s.MASACH, s.ISBN, i.TENSACH, s.TINHTRANG, s.CHOMUON, ISNULL(i.GIA, 0) AS GiaBia
    FROM dbo.SACH s
    INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
    WHERE s.MASACH = LTRIM(RTRIM(@MASACH));
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Sach_Them
    @MASACH    VARCHAR(20),
    @ISBN      VARCHAR(20),
    @MANGANTU  INT = NULL,
    @TINHTRANG BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @MASACH = NULLIF(LTRIM(RTRIM(@MASACH)), '');
    SET @ISBN = NULLIF(LTRIM(RTRIM(@ISBN)), '');

    IF @MASACH IS NULL OR LEN(@MASACH) > 10
        THROW 53101, N'Mã cuốn sách là bắt buộc và tối đa 10 ký tự!', 1;
    IF @ISBN IS NULL
        THROW 53102, N'Vui lòng chọn đầu sách (ISBN)!', 1;
    IF @MANGANTU IS NULL
        THROW 53103, N'Vui lòng chọn ngăn tủ / kệ cho cuốn sách!', 1;

    INSERT INTO dbo.SACH (MASACH, ISBN, TINHTRANG, CHOMUON, MANGANTU)
    VALUES (@MASACH, @ISBN, ISNULL(@TINHTRANG, 1), 0, @MANGANTU);
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Sach_CapNhat
    @MASACH    VARCHAR(20),
    @ISBN      VARCHAR(20),
    @MANGANTU  INT = NULL,
    @TINHTRANG BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @MASACH = LTRIM(RTRIM(@MASACH));
    SET @ISBN = NULLIF(LTRIM(RTRIM(@ISBN)), '');

    IF NOT EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH = @MASACH)
        THROW 53104, N'Không tìm thấy cuốn sách; vui lòng làm mới danh sách!', 1;
    IF @ISBN IS NULL
        THROW 53102, N'Vui lòng chọn đầu sách (ISBN)!', 1;
    IF @MANGANTU IS NULL
        THROW 53103, N'Vui lòng chọn ngăn tủ / kệ cho cuốn sách!', 1;

    UPDATE dbo.SACH
    SET ISBN = @ISBN, MANGANTU = @MANGANTU, TINHTRANG = ISNULL(@TINHTRANG, 1)
    WHERE MASACH = @MASACH;
END;
GO

/* 1 = good, 0 = damaged / withdrawn. */
CREATE OR ALTER PROCEDURE dbo.sp_Sach_CapNhatTinhTrang
    @MASACH    VARCHAR(20),
    @TINHTRANG BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @MASACH = LTRIM(RTRIM(@MASACH));
    IF NOT EXISTS (SELECT 1 FROM dbo.SACH WHERE MASACH = @MASACH)
        THROW 53104, N'Không tìm thấy cuốn sách; vui lòng làm mới danh sách!', 1;

    UPDATE dbo.SACH SET TINHTRANG = ISNULL(@TINHTRANG, 0) WHERE MASACH = @MASACH;
END;
GO

/* Remove a copy permanently. On-loan copies are refused; loan history -> FK 547. */
CREATE OR ALTER PROCEDURE dbo.sp_Sach_Huy
    @MASACH VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ChoMuon BIT;
    SET @MASACH = LTRIM(RTRIM(@MASACH));

    SELECT @ChoMuon = CHOMUON FROM dbo.SACH WHERE MASACH = @MASACH;

    IF @ChoMuon IS NULL
        THROW 53105, N'Không tìm thấy cuốn sách này trong hệ thống!', 1;
    IF @ChoMuon = 1
        THROW 53106, N'Sách đang được mượn, không thể tiến hành hủy!', 1;

    DELETE FROM dbo.SACH WHERE MASACH = @MASACH;
END;
GO

/* ======================================================================
   BOOKS: titles (ISBN + TACGIA_SACH)
   ====================================================================== */

/* List / search titles with authors and copy counts. */
CREATE OR ALTER PROCEDURE dbo.sp_DauSach_DanhSach
    @Keyword NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Pattern NVARCHAR(102) = N'%' + ISNULL(LTRIM(RTRIM(@Keyword)), N'') + N'%';

    WITH SachStats AS (
        SELECT
            s.ISBN,
            COUNT(*) AS TongBanSao,
            SUM(CASE WHEN s.CHOMUON = 0 AND s.TINHTRANG = 1 THEN 1 ELSE 0 END) AS BanSaoKhaDung
        FROM dbo.SACH s
        GROUP BY s.ISBN
    )
    SELECT
        RTRIM(i.ISBN) AS ISBN,
        i.TENSACH,
        ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI,
        ISNULL((
            SELECT STRING_AGG(tg.HOTENTG, ', ')
            FROM dbo.TACGIA_SACH tgs
            JOIN dbo.TACGIA tg ON tgs.MATACGIA = tg.MATACGIA
            WHERE tgs.ISBN = i.ISBN
        ), N'Chưa rõ') AS HOTENTG,
        ISNULL(nn.NGONNGU, N'Chưa rõ') AS NGONNGU,
        i.SOTRANG,
        ISNULL(i.GIA, 0) AS GIA,
        ISNULL(i.GIA, 0) AS GiaBia,
        ISNULL(i.NHAXB, N'') AS NHAXB,
        i.LANXUATBAN,
        ISNULL(st.TongBanSao, 0) AS TongBanSao,
        ISNULL(st.BanSaoKhaDung, 0) AS BanSaoKhaDung
    FROM dbo.ISBN i
    LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
    LEFT JOIN dbo.NGONNGU nn ON i.MANGONNGU = nn.MANGONNGU
    LEFT JOIN SachStats st ON st.ISBN = i.ISBN
    WHERE i.ISBN LIKE @Pattern
       OR i.TENSACH LIKE @Pattern
       OR i.NHAXB LIKE @Pattern
       OR tl.THELOAI LIKE @Pattern
       OR EXISTS (
           SELECT 1 FROM dbo.TACGIA_SACH tgs2
           JOIN dbo.TACGIA tg2 ON tgs2.MATACGIA = tg2.MATACGIA
           WHERE tgs2.ISBN = i.ISBN AND tg2.HOTENTG LIKE @Pattern
       )
    ORDER BY i.ISBN ASC;
END;
GO

/* One title with its main author (fills the edit form). */
CREATE OR ALTER PROCEDURE dbo.sp_DauSach_ChiTiet
    @ISBN VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT i.ISBN, i.TENSACH, i.GIA, i.MATL, i.MANGONNGU, i.NHAXB, i.SOTRANG,
           i.KHOSACH, i.LANXUATBAN, i.NOIDUNG,
           (SELECT TOP (1) MATACGIA FROM dbo.TACGIA_SACH t
            WHERE t.ISBN = i.ISBN ORDER BY MATACGIA) AS MATACGIA
    FROM dbo.ISBN i
    WHERE i.ISBN = LTRIM(RTRIM(@ISBN));
END;
GO

/* Add a title and (optionally) its main author in one transaction. */
CREATE OR ALTER PROCEDURE dbo.sp_DauSach_Them
    @ISBN        VARCHAR(20),
    @TENSACH     NVARCHAR(100),
    @KHOSACH     NVARCHAR(5)   = NULL,
    @NOIDUNG     NVARCHAR(300) = NULL,
    @SOTRANG     INT           = NULL,
    @GIA         BIGINT        = NULL,
    @HINHANHPATH NVARCHAR(50)  = NULL,
    @NGAYXUATBAN SMALLDATETIME = NULL,
    @LANXUATBAN  INT           = 1,
    @NHAXB       NVARCHAR(100) = NULL,
    @MANGONNGU   INT           = NULL,
    @MATL        CHAR(5)       = NULL,
    @MATACGIA    INT           = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @ISBN = NULLIF(LTRIM(RTRIM(@ISBN)), '');
    SET @TENSACH = NULLIF(LTRIM(RTRIM(@TENSACH)), N'');

    IF @ISBN IS NULL OR LEN(@ISBN) > 10
        THROW 53111, N'Mã ISBN là bắt buộc và tối đa 10 ký tự!', 1;
    IF @TENSACH IS NULL
        THROW 53112, N'Tên đầu sách không được để trống!', 1;
    IF @GIA < 0
        THROW 53113, N'Giá bìa không được âm!', 1;
    IF @MATL IS NULL OR @MANGONNGU IS NULL
        THROW 53114, N'Vui lòng chọn thể loại và ngôn ngữ cho đầu sách!', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO dbo.ISBN (ISBN, TENSACH, KHOSACH, NOIDUNG, SOTRANG, GIA,
                              HINHANHPATH, NGAYXUATBAN, LANXUATBAN, NHAXB, MANGONNGU, MATL)
        VALUES (@ISBN, @TENSACH, NULLIF(@KHOSACH, N''), NULLIF(@NOIDUNG, N''), @SOTRANG, @GIA,
                @HINHANHPATH, @NGAYXUATBAN, ISNULL(@LANXUATBAN, 1), NULLIF(@NHAXB, N''),
                @MANGONNGU, @MATL);

        IF @MATACGIA IS NOT NULL
            INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES (@MATACGIA, @ISBN);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

/* Edit a title (ISBN key unchanged) and replace its main author, in one transaction. */
CREATE OR ALTER PROCEDURE dbo.sp_DauSach_CapNhat
    @ISBN       VARCHAR(20),
    @TENSACH    NVARCHAR(100),
    @GIA        BIGINT        = NULL,
    @MATL       CHAR(5)       = NULL,
    @MANGONNGU  INT           = NULL,
    @NHAXB      NVARCHAR(100) = NULL,
    @SOTRANG    INT           = NULL,
    @KHOSACH    NVARCHAR(5)   = NULL,
    @LANXUATBAN INT           = 1,
    @NOIDUNG    NVARCHAR(300) = NULL,
    @MATACGIA   INT           = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @ISBN = LTRIM(RTRIM(@ISBN));
    SET @TENSACH = NULLIF(LTRIM(RTRIM(@TENSACH)), N'');

    IF @TENSACH IS NULL
        THROW 53112, N'Tên đầu sách không được để trống!', 1;
    IF @GIA < 0
        THROW 53113, N'Giá bìa không được âm!', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.ISBN WITH (UPDLOCK, HOLDLOCK) WHERE ISBN = @ISBN)
            THROW 53115, N'Không tìm thấy đầu sách; vui lòng làm mới danh sách!', 1;

        IF @MATACGIA IS NOT NULL
        BEGIN
            DELETE FROM dbo.TACGIA_SACH WHERE ISBN = @ISBN AND MATACGIA <> @MATACGIA;
            IF NOT EXISTS (SELECT 1 FROM dbo.TACGIA_SACH WHERE ISBN = @ISBN AND MATACGIA = @MATACGIA)
                INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES (@MATACGIA, @ISBN);
        END;

        UPDATE dbo.ISBN
        SET TENSACH = @TENSACH, GIA = @GIA,
            MATL = ISNULL(@MATL, MATL), MANGONNGU = ISNULL(@MANGONNGU, MANGONNGU),
            NHAXB = NULLIF(@NHAXB, N''), SOTRANG = @SOTRANG, KHOSACH = NULLIF(@KHOSACH, N''),
            LANXUATBAN = ISNULL(@LANXUATBAN, 1), NOIDUNG = NULLIF(@NOIDUNG, N'')
        WHERE ISBN = @ISBN;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

/* Delete a title. Copies still on file -> FK_SACH_ISBN (547), whole delete rolled back. */
CREATE OR ALTER PROCEDURE dbo.sp_DauSach_Xoa
    @ISBN VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SET @ISBN = LTRIM(RTRIM(@ISBN));
    IF NOT EXISTS (SELECT 1 FROM dbo.ISBN WHERE ISBN = @ISBN)
        THROW 53115, N'Không tìm thấy đầu sách; vui lòng làm mới danh sách!', 1;

    BEGIN TRY
        BEGIN TRANSACTION;
        DELETE FROM dbo.TACGIA_SACH WHERE ISBN = @ISBN;
        DELETE FROM dbo.ISBN WHERE ISBN = @ISBN;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

/* ======================================================================
   PERMISSIONS
   QUANLY already has EXECUTE ON SCHEMA::dbo (03_login_and_permissions.sql).
   THUTHU gets the same reach it has on the tables: full reader management,
   read-only books, plus the copy-condition update (it has UPDATE on SACH).
   library_app_role (smoke tests) gets everything.
   ====================================================================== */
IF DATABASE_PRINCIPAL_ID(N'THUTHU') IS NOT NULL
BEGIN
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_DanhSach         TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_DanhSachHoatDong TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_ChiTiet          TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_KiemTraTrung     TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_Them             TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_CapNhat          TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_Xoa              TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_GiaHan           TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_DoiTrangThai     TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_CapLaiThe        TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DocGia_KiemTraMuonSach  TO [THUTHU];

    GRANT EXECUTE ON OBJECT::dbo.sp_DanhMuc_TheLoai         TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DanhMuc_NganTu          TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DanhMuc_TacGia          TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DanhMuc_NgonNgu         TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_Sach_DanhSach           TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_Sach_SanSangChoMuon     TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_Sach_KiemTraChoMuon     TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_Sach_CapNhatTinhTrang   TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DauSach_DanhSach        TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_DauSach_ChiTiet         TO [THUTHU];
END;

/* Per object, never ON SCHEMA: a schema-wide grant would also reach the
   certificate-signed account-administration procedures. */
IF DATABASE_PRINCIPAL_ID(N'library_app_role') IS NOT NULL
BEGIN
    DECLARE @GrantSql NVARCHAR(MAX) = N'';
    SELECT @GrantSql += N'GRANT EXECUTE ON OBJECT::dbo.' + QUOTENAME(name)
                      + N' TO [library_app_role];' + NCHAR(10)
    FROM sys.procedures
    WHERE schema_id = SCHEMA_ID(N'dbo')
      AND (name LIKE N'sp[_]DocGia[_]%' OR name LIKE N'sp[_]Sach[_]%'
           OR name LIKE N'sp[_]DauSach[_]%' OR name LIKE N'sp[_]DanhMuc[_]%');
    EXEC sys.sp_executesql @GrantSql;
END;
GO
