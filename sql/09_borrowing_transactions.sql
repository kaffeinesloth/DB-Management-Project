/*
    Library Management System - Borrowing and returns as server-side transactions

    Task 4 (data integrity and TRANSACTION). Lending a book and taking it back
    each change several tables at once (PHIEUMUON, CT_PHIEUMUON, SACH). These
    procedures do the whole change inside one BEGIN TRANSACTION ... COMMIT,
    with BEGIN TRY / BEGIN CATCH + ROLLBACK, so a failure leaves nothing half
    written. The Python client only sends EXEC.

    Conventions (same as 08_server_side_crud.sql)
    - SET NOCOUNT ON and SET XACT_ABORT ON.
    - Business rules are raised with THROW and a Vietnamese message:
        5410x = lending, 5411x = returns.
    - Results are returned by a final SELECT after COMMIT.

    How SACH.CHOMUON is kept in step
    trg_SACH_EnforceLoanState (01_create_tables.sql) rejects any SACH row whose
    CHOMUON disagrees with the active CT_PHIEUMUON rows (THROW 50015), and
    trg_CT_PHIEUMUON_ValidateAndSync sets CHOMUON from those rows. So a
    procedure cannot write CHOMUON = 1 before the loan line exists. Instead:
    - lending takes UPDLOCK + HOLDLOCK on the requested SACH rows, checks that
      every one is CHOMUON = 0 AND TINHTRANG = 1, then inserts the loan lines;
      the trigger then sets CHOMUON = 1. The update lock is held until COMMIT,
      so a second librarian lending the same copy waits, then sees CHOMUON = 1
      and gets THROW 54105. Same guarantee as an "UPDATE ... WHERE CHOMUON = 0".
    - returning updates CT_PHIEUMUON first, then SACH (CHOMUON = 0 now agrees
      with the loan lines, and TINHTRANG = 0 records a lost or damaged copy).

    Lending locks DOCGIA before SACH, the same order the trigger uses, to
    avoid deadlocks between concurrent borrowers.

    Run after 03_login_and_permissions.sql (grants need the roles). Safe to re-run.
*/

:on error exit

USE [LibraryManagement];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ======================================================================
   LEND: one PHIEUMUON with 1 to 3 copies
   ====================================================================== */
CREATE OR ALTER PROCEDURE dbo.sp_PhieuMuon_Tao
    @MADG           BIGINT,
    @MANV           INT,
    @HinhThuc       BIT,             -- 1 = take home (30-day due date), 0 = read in the library
    @DanhSachMaSach NVARCHAR(500)    -- copy codes separated by commas, e.g. N'S0001,S0002'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @MaxBooks INT = 3;
    DECLARE @Requested TABLE (MASACH NVARCHAR(500) NOT NULL);
    DECLARE @Locked TABLE (MASACH VARCHAR(10) NOT NULL PRIMARY KEY);
    DECLARE @SoSach INT, @SoSachKhacNhau INT, @DangGiu INT;
    DECLARE @Found BIT = 0, @HoatDong BIT, @NgayHetHan SMALLDATETIME, @SOCMND VARCHAR(12);
    DECLARE @NewMaPhieu BIGINT, @Msg NVARCHAR(2048);

    IF @MANV IS NULL OR @HinhThuc IS NULL
        THROW 54107, N'Thiếu mã nhân viên lập phiếu hoặc hình thức mượn!', 1;

    INSERT INTO @Requested (MASACH)
    SELECT LTRIM(RTRIM(value))
    FROM STRING_SPLIT(ISNULL(@DanhSachMaSach, N''), N',')
    WHERE LTRIM(RTRIM(value)) <> N'';

    SELECT @SoSach = COUNT(*), @SoSachKhacNhau = COUNT(DISTINCT MASACH) FROM @Requested;

    IF @SoSach < 1 OR @SoSach > @MaxBooks
        THROW 54101, N'Mỗi phiếu mượn phải có từ 1 đến 3 cuốn sách!', 1;
    IF @SoSachKhacNhau <> @SoSach
        THROW 54106, N'Các mã sách trong cùng một phiếu mượn không được trùng nhau!', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        /* 1. Reader card: lock it so two loans for one reader run one at a time. */
        SELECT @Found = 1, @HoatDong = HOATDONG, @NgayHetHan = NGAYHETHAN, @SOCMND = SOCMND
        FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
        WHERE MADG = @MADG;

        IF @Found = 0
        BEGIN
            SET @Msg = N'Không tìm thấy thẻ độc giả mã ' + CAST(@MADG AS NVARCHAR(20)) + N'!';
            THROW 54102, @Msg, 1;
        END;
        IF @HoatDong = 0
            THROW 54102, N'Thẻ độc giả đang bị KHÓA! Không thể mượn sách.', 1;
        IF @NgayHetHan < GETDATE()
        BEGIN
            SET @Msg = N'Thẻ độc giả đã HẾT HẠN từ ngày ' + CONVERT(NVARCHAR(10), @NgayHetHan, 103)
                     + N'! Vui lòng gia hạn thẻ.';
            THROW 54103, @Msg, 1;
        END;

        /* 2. At most 3 unreturned books per person (all cards with the same SOCMND,
              the same rule as sp_DocGia_KiemTraMuonSach). */
        SELECT @DangGiu = COUNT(*)
        FROM dbo.CT_PHIEUMUON AS ct
        INNER JOIN dbo.PHIEUMUON AS pm ON pm.MAPHIEU = ct.MAPHIEU
        INNER JOIN dbo.DOCGIA AS dg ON dg.MADG = pm.MADG
        WHERE dg.SOCMND = @SOCMND AND ct.TRA = 0;

        IF @DangGiu + @SoSach > @MaxBooks
        BEGIN
            SET @Msg = N'Độc giả đang giữ ' + CAST(@DangGiu AS NVARCHAR(10)) + N' cuốn. Muốn mượn thêm '
                     + CAST(@SoSach AS NVARCHAR(10)) + N' cuốn sẽ vượt quá giới hạn tối đa 3 cuốn/độc giả!';
            THROW 54104, @Msg, 1;
        END;

        /* 3. Atomic check-and-lock of the copies (see the header for why this is
              UPDLOCK rather than UPDATE ... SET CHOMUON = 1). */
        INSERT INTO @Locked (MASACH)
        SELECT book.MASACH
        FROM dbo.SACH AS book WITH (UPDLOCK, ROWLOCK, HOLDLOCK)
        INNER JOIN @Requested AS req ON req.MASACH = book.MASACH
        WHERE book.CHOMUON = 0 AND book.TINHTRANG = 1;

        IF @@ROWCOUNT <> @SoSach
        BEGIN
            SELECT @Msg = N'Sách ' + STRING_AGG(req.MASACH, N', ')
                        + N' đã có người khác mượn, đang hư hỏng hoặc không tồn tại!'
            FROM @Requested AS req
            WHERE NOT EXISTS (SELECT 1 FROM @Locked AS lk WHERE lk.MASACH = req.MASACH);
            THROW 54105, @Msg, 1;
        END;

        /* 4. Loan header and lines. The CT_PHIEUMUON trigger sets SACH.CHOMUON = 1. */
        INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV)
        VALUES (@MADG, @HinhThuc, GETDATE(), @MANV);

        SET @NewMaPhieu = CAST(SCOPE_IDENTITY() AS BIGINT);

        INSERT INTO dbo.CT_PHIEUMUON (MAPHIEU, MASACH, TINHTRANGMUON, TRA)
        SELECT @NewMaPhieu, MASACH, 1, 0
        FROM @Locked;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @NewMaPhieu AS MAPHIEU;
END;
GO

/* ======================================================================
   RETURN one copy, with the fine
   Late fee: 500 VND per day past the 30-day due date (v_ChiTietPhieuMuon_Phat).
   Lost: 100% of the cover price. Damaged (borrowed good, returned damaged): 50%.
   ====================================================================== */
CREATE OR ALTER PROCEDURE dbo.sp_PhieuMuon_XacNhanTra
    @MAPHIEU      BIGINT,
    @MASACH       VARCHAR(10),
    @MANVNS       INT,
    @TinhTrangTra BIT = 1,           -- 1 = good, 0 = damaged
    @BiMat        BIT = 0            -- 1 = lost
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Found BIT = 0;
    DECLARE @TenSach NVARCHAR(100), @GiaBia BIGINT, @SoNgayDaMuon INT, @SoNgayTre INT;
    DECLARE @TienPhatTre BIGINT, @TienMatSach BIGINT, @TienPhatHong BIGINT, @TinhTrangMuon BIT;

    IF @MANVNS IS NULL OR @TinhTrangTra IS NULL OR @BiMat IS NULL
        THROW 54112, N'Thiếu mã nhân viên nhận sách hoặc tình trạng sách trả!', 1;

    SET @MASACH = LTRIM(RTRIM(@MASACH));

    BEGIN TRY
        BEGIN TRANSACTION;

        /* 1. The loan line must exist and still be open; lock it against a double return. */
        SELECT @Found = 1
        FROM dbo.CT_PHIEUMUON WITH (UPDLOCK, HOLDLOCK)
        WHERE MAPHIEU = @MAPHIEU AND MASACH = @MASACH AND TRA = 0;

        IF @Found = 0
            THROW 54111, N'Không tìm thấy lượt mượn chưa trả của cuốn sách này (có thể đã được trả trước đó)!', 1;

        /* 2. Fine, read before NGAYTRA is written (the view uses GETDATE() while open). */
        SELECT @TenSach = TENSACH, @GiaBia = GiaBia, @SoNgayDaMuon = SoNgayDaMuon,
               @SoNgayTre = SoNgayTre, @TienPhatTre = TienPhatTre, @TinhTrangMuon = TINHTRANGMUON
        FROM dbo.v_ChiTietPhieuMuon_Phat
        WHERE MAPHIEU = @MAPHIEU AND MASACH = @MASACH;

        SET @TienMatSach  = CASE WHEN @BiMat = 1 THEN @GiaBia ELSE 0 END;
        SET @TienPhatHong = CASE WHEN @BiMat = 0 AND @TinhTrangTra = 0 AND @TinhTrangMuon = 1
                                 THEN @GiaBia / 2 ELSE 0 END;

        /* 3. Close the loan line (the trigger also syncs SACH.CHOMUON). */
        UPDATE dbo.CT_PHIEUMUON
        SET TRA = 1, NGAYTRA = GETDATE(), MANVNS = @MANVNS
        WHERE MAPHIEU = @MAPHIEU AND MASACH = @MASACH AND TRA = 0;

        /* 4. Copy is back on the shelf; lost or damaged copies become unusable. */
        UPDATE dbo.SACH
        SET CHOMUON = 0,
            TINHTRANG = CASE WHEN @BiMat = 1 OR @TinhTrangTra = 0 THEN 0 ELSE TINHTRANG END
        WHERE MASACH = @MASACH;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @MAPHIEU AS MAPHIEU,
           @MASACH AS MASACH,
           @TenSach AS TENSACH,
           @GiaBia AS GiaBia,
           @SoNgayDaMuon AS SoNgayDaMuon,
           @SoNgayTre AS SoNgayTre,
           @TienPhatTre AS TienPhatTre,
           @TienMatSach AS TienMatSach,
           @TienPhatHong AS TienPhatHong,
           @TienPhatTre + @TienMatSach + @TienPhatHong AS TongPhat;
END;
GO

/* ======================================================================
   RETURN several copies of one title (ISBN) from one PHIEUMUON.
   Picks @SoLuong unreturned copies of that title and returns them together.
   ====================================================================== */
CREATE OR ALTER PROCEDURE dbo.sp_PhieuMuon_TraTheoISBN
    @MAPHIEU      BIGINT,
    @ISBN         CHAR(10),
    @SoLuong      INT,
    @MANVNS       INT,
    @TinhTrangTra BIT = 1,
    @BiMat        BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Chosen TABLE (MASACH VARCHAR(10) NOT NULL PRIMARY KEY);
    DECLARE @SoCuonChon INT;
    DECLARE @TienPhatTre BIGINT, @TienMatSach BIGINT, @TienPhatHong BIGINT;
    DECLARE @Msg NVARCHAR(2048);

    IF @MANVNS IS NULL OR @TinhTrangTra IS NULL OR @BiMat IS NULL
        THROW 54112, N'Thiếu mã nhân viên nhận sách hoặc tình trạng sách trả!', 1;
    IF @SoLuong IS NULL OR @SoLuong < 1
        THROW 54113, N'Số lượng sách trả phải lớn hơn 0!', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        /* 1. Choose and lock @SoLuong open loan lines of this title. */
        INSERT INTO @Chosen (MASACH)
        SELECT TOP (@SoLuong) ct.MASACH
        FROM dbo.CT_PHIEUMUON AS ct WITH (UPDLOCK, HOLDLOCK)
        INNER JOIN dbo.SACH AS book ON book.MASACH = ct.MASACH
        WHERE ct.MAPHIEU = @MAPHIEU AND book.ISBN = @ISBN AND ct.TRA = 0
        ORDER BY ct.MASACH;

        SET @SoCuonChon = @@ROWCOUNT;
        IF @SoCuonChon < @SoLuong
        BEGIN
            SET @Msg = N'Số sách chưa trả của ISBN ' + RTRIM(@ISBN) + N' chỉ còn '
                     + CAST(@SoCuonChon AS NVARCHAR(10)) + N' cuốn, không đủ để trả '
                     + CAST(@SoLuong AS NVARCHAR(10)) + N' cuốn!';
            THROW 54114, @Msg, 1;
        END;

        /* 2. Fines, summed over the chosen copies. */
        SELECT @TienPhatTre  = SUM(v.TienPhatTre),
               @TienMatSach  = SUM(CASE WHEN @BiMat = 1 THEN v.GiaBia ELSE 0 END),
               @TienPhatHong = SUM(CASE WHEN @BiMat = 0 AND @TinhTrangTra = 0 AND v.TINHTRANGMUON = 1
                                        THEN v.GiaBia / 2 ELSE 0 END)
        FROM dbo.v_ChiTietPhieuMuon_Phat AS v
        INNER JOIN @Chosen AS c ON c.MASACH = v.MASACH
        WHERE v.MAPHIEU = @MAPHIEU;

        /* 3. Close the loan lines, then 4. update the copies. */
        UPDATE ct
        SET TRA = 1, NGAYTRA = GETDATE(), MANVNS = @MANVNS
        FROM dbo.CT_PHIEUMUON AS ct
        INNER JOIN @Chosen AS c ON c.MASACH = ct.MASACH
        WHERE ct.MAPHIEU = @MAPHIEU AND ct.TRA = 0;

        UPDATE book
        SET CHOMUON = 0,
            TINHTRANG = CASE WHEN @BiMat = 1 OR @TinhTrangTra = 0 THEN 0 ELSE book.TINHTRANG END
        FROM dbo.SACH AS book
        INNER JOIN @Chosen AS c ON c.MASACH = book.MASACH;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @MAPHIEU AS MAPHIEU,
           @ISBN AS ISBN,
           @SoCuonChon AS SoCuonTra,
           @TienPhatTre AS TienPhatTre,
           @TienMatSach AS TienMatSach,
           @TienPhatHong AS TienPhatHong,
           @TienPhatTre + @TienMatSach + @TienPhatHong AS TongPhat;
END;
GO

/* ======================================================================
   PERMISSIONS
   QUANLY already has EXECUTE ON SCHEMA::dbo; the explicit grants document
   that both staff roles may lend and take back books. library_app_role is
   the account the smoke tests run as.
   ====================================================================== */
IF DATABASE_PRINCIPAL_ID(N'QUANLY') IS NOT NULL
BEGIN
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_Tao         TO [QUANLY];
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_XacNhanTra  TO [QUANLY];
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_TraTheoISBN TO [QUANLY];
END;

IF DATABASE_PRINCIPAL_ID(N'THUTHU') IS NOT NULL
BEGIN
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_Tao         TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_XacNhanTra  TO [THUTHU];
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_TraTheoISBN TO [THUTHU];
END;

IF DATABASE_PRINCIPAL_ID(N'library_app_role') IS NOT NULL
BEGIN
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_Tao         TO [library_app_role];
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_XacNhanTra  TO [library_app_role];
    GRANT EXECUTE ON OBJECT::dbo.sp_PhieuMuon_TraTheoISBN TO [library_app_role];
END;
GO
