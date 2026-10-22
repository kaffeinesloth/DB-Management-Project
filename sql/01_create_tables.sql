/*
    Library Management System - SQL Server schema

    Based on De4-QLTV_Unicode_Fixed.docx.

    Source clarifications applied:
    - Unicode descriptive text uses NVARCHAR.
    - ISBN is CHAR(10) everywhere so its foreign keys are type-compatible.
    - MASACH is VARCHAR(10) everywhere; the document lists VARCHAR(20) only in
      CT_PHIEUMUON, which would be incompatible with SACH.MASACH.
    - DOCGIA.DIACHI and DOCGIA.DIENTHOAI have no types or lengths in the
      document. They use NVARCHAR(100) and VARCHAR(11), consistent with the
      equivalent NHANVIEN fields.
    - NHAXB and NGANTU.KE are stored as descriptive text. The document marks
      them as foreign keys but defines no referenced NHAXB or KE table.
    - A lost card receives a new MADG. SOCMND is therefore unique only among
      active cards, allowing the same person to keep inactive card history.
    - The required 30-day loan period and 500 VND daily overdue fine are
      calculated in reporting views; no extra table is added to the 11-table
      model because the document defines no fine entity.
*/

IF DB_ID(N'LibraryManagement') IS NULL
BEGIN
    EXEC(N'CREATE DATABASE [LibraryManagement]');
END;
GO

USE [LibraryManagement];
GO

/* Required by SQL Server for filtered indexes and persisted object metadata. */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.THELOAI', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.THELOAI
    (
        MATL        CHAR(5)       NOT NULL,
        THELOAI     NVARCHAR(50)  NOT NULL,
        CONSTRAINT PK_THELOAI PRIMARY KEY (MATL),
        CONSTRAINT UQ_THELOAI_TEN UNIQUE (THELOAI)
    );
END;
GO

IF OBJECT_ID(N'dbo.NGONNGU', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.NGONNGU
    (
        MANGONNGU   INT           IDENTITY(1,1) NOT NULL,
        NGONNGU     NVARCHAR(50)  NOT NULL,
        CONSTRAINT PK_NGONNGU PRIMARY KEY (MANGONNGU),
        CONSTRAINT UQ_NGONNGU_TEN UNIQUE (NGONNGU)
    );
END;
GO

IF OBJECT_ID(N'dbo.NGANTU', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.NGANTU
    (
        MANGANTU    INT            IDENTITY(1,1) NOT NULL,
        MOTA        NVARCHAR(50)   NULL,
        KE          NVARCHAR(100)  NOT NULL,
        CONSTRAINT PK_NGANTU PRIMARY KEY (MANGANTU)
    );
END;
GO

IF OBJECT_ID(N'dbo.TACGIA', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.TACGIA
    (
        MATACGIA      INT            IDENTITY(1,1) NOT NULL,
        HOTENTG       NVARCHAR(50)   NOT NULL,
        DIACHITG      NVARCHAR(100)  NULL,
        DIENTHOAITG   VARCHAR(11)    NULL,
        CONSTRAINT PK_TACGIA PRIMARY KEY (MATACGIA)
    );
END;
GO

IF OBJECT_ID(N'dbo.DOCGIA', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.DOCGIA
    (
        MADG          BIGINT         IDENTITY(1,1) NOT NULL,
        HODG          NVARCHAR(50)   NOT NULL,
        TENDG         NVARCHAR(12)   NOT NULL,
        EMAILDG       NVARCHAR(50)   NULL,
        SOCMND        VARCHAR(12)    NOT NULL,
        GIOITINH      BIT            NULL,
        NGAYSINH      SMALLDATETIME  NULL,
        DIACHI        NVARCHAR(100)  NULL,
        DIENTHOAI     VARCHAR(11)    NULL,
        NGAYLAMTHE    SMALLDATETIME  NOT NULL
            CONSTRAINT DF_DOCGIA_NGAYLAMTHE DEFAULT (GETDATE()),
        NGAYHETHAN    SMALLDATETIME  NOT NULL,
        HOATDONG      BIT            NOT NULL
            CONSTRAINT DF_DOCGIA_HOATDONG DEFAULT (1),
        CONSTRAINT PK_DOCGIA PRIMARY KEY (MADG),
        CONSTRAINT CK_DOCGIA_NGAYHETHAN CHECK (NGAYHETHAN >= NGAYLAMTHE)
    );
END;
GO

/* Support replacement cards while preventing two active cards for one person. */
IF EXISTS
(
    SELECT 1
    FROM sys.key_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.DOCGIA')
      AND name = N'UQ_DOCGIA_SOCMND'
)
BEGIN
    ALTER TABLE dbo.DOCGIA DROP CONSTRAINT UQ_DOCGIA_SOCMND;
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.DOCGIA')
      AND name = N'UX_DOCGIA_SOCMND_ACTIVE'
)
BEGIN
    CREATE UNIQUE INDEX UX_DOCGIA_SOCMND_ACTIVE
        ON dbo.DOCGIA (SOCMND)
        WHERE HOATDONG = 1;
END;
GO

IF OBJECT_ID(N'dbo.NHANVIEN', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.NHANVIEN
    (
        MANV          INT            IDENTITY(1,1) NOT NULL,
        HONV          NVARCHAR(50)   NOT NULL,
        TENNV         NVARCHAR(12)   NOT NULL,
        GIOITINH      BIT            NULL,
        DIACHI        NVARCHAR(100)  NULL,
        DIENTHOAI     VARCHAR(11)    NULL,
        EMAIL         VARCHAR(50)    NULL,
        CONSTRAINT PK_NHANVIEN PRIMARY KEY (MANV)
    );
END;
GO

IF OBJECT_ID(N'dbo.ISBN', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ISBN
    (
        ISBN          CHAR(10)        NOT NULL,
        TENSACH       NVARCHAR(100)   NOT NULL,
        KHOSACH       NVARCHAR(5)     NULL,
        NOIDUNG       NVARCHAR(300)   NULL,
        HINHANHPATH   NVARCHAR(50)    NULL,
        NGAYXUATBAN   SMALLDATETIME   NULL,
        LANXUATBAN    INT             NULL,
        SOTRANG       INT             NULL,
        GIA           BIGINT          NULL,
        NHAXB         NVARCHAR(100)   NULL,
        MANGONNGU     INT             NOT NULL,
        MATL          CHAR(5)         NOT NULL,
        CONSTRAINT PK_ISBN PRIMARY KEY (ISBN),
        CONSTRAINT FK_ISBN_NGONNGU FOREIGN KEY (MANGONNGU)
            REFERENCES dbo.NGONNGU (MANGONNGU),
        CONSTRAINT FK_ISBN_THELOAI FOREIGN KEY (MATL)
            REFERENCES dbo.THELOAI (MATL),
        CONSTRAINT CK_ISBN_LANXUATBAN CHECK (LANXUATBAN IS NULL OR LANXUATBAN > 0),
        CONSTRAINT CK_ISBN_SOTRANG CHECK (SOTRANG IS NULL OR SOTRANG > 0),
        CONSTRAINT CK_ISBN_GIA CHECK (GIA IS NULL OR GIA >= 0)
    );
END;
GO

IF OBJECT_ID(N'dbo.SACH', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.SACH
    (
        MASACH        VARCHAR(10)  NOT NULL,
        ISBN          CHAR(10)     NOT NULL,
        TINHTRANG     BIT          NOT NULL
            CONSTRAINT DF_SACH_TINHTRANG DEFAULT (1),
        CHOMUON       BIT          NOT NULL
            CONSTRAINT DF_SACH_CHOMUON DEFAULT (0),
        MANGANTU      INT          NOT NULL,
        CONSTRAINT PK_SACH PRIMARY KEY (MASACH),
        CONSTRAINT FK_SACH_ISBN FOREIGN KEY (ISBN)
            REFERENCES dbo.ISBN (ISBN),
        CONSTRAINT FK_SACH_NGANTU FOREIGN KEY (MANGANTU)
            REFERENCES dbo.NGANTU (MANGANTU)
    );
END;
GO

IF OBJECT_ID(N'dbo.TACGIA_SACH', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.TACGIA_SACH
    (
        MATACGIA      INT       NOT NULL,
        ISBN          CHAR(10)  NOT NULL,
        CONSTRAINT PK_TACGIA_SACH PRIMARY KEY (MATACGIA, ISBN),
        CONSTRAINT FK_TACGIA_SACH_TACGIA FOREIGN KEY (MATACGIA)
            REFERENCES dbo.TACGIA (MATACGIA),
        CONSTRAINT FK_TACGIA_SACH_ISBN FOREIGN KEY (ISBN)
            REFERENCES dbo.ISBN (ISBN)
    );
END;
GO

IF OBJECT_ID(N'dbo.PHIEUMUON', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.PHIEUMUON
    (
        MAPHIEU       BIGINT         IDENTITY(1,1) NOT NULL,
        MADG          BIGINT         NOT NULL,
        HINHTHUC      BIT            NOT NULL,
        NGAYMUON      SMALLDATETIME  NOT NULL
            CONSTRAINT DF_PHIEUMUON_NGAYMUON DEFAULT (GETDATE()),
        MANV          INT            NOT NULL,
        CONSTRAINT PK_PHIEUMUON PRIMARY KEY (MAPHIEU),
        CONSTRAINT FK_PHIEUMUON_DOCGIA FOREIGN KEY (MADG)
            REFERENCES dbo.DOCGIA (MADG),
        CONSTRAINT FK_PHIEUMUON_NHANVIEN FOREIGN KEY (MANV)
            REFERENCES dbo.NHANVIEN (MANV)
    );
END;
GO

IF OBJECT_ID(N'dbo.CT_PHIEUMUON', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.CT_PHIEUMUON
    (
        MAPHIEU          BIGINT         NOT NULL,
        MASACH           VARCHAR(10)    NOT NULL,
        NGAYTRA          SMALLDATETIME  NULL,
        TINHTRANGMUON    BIT            NOT NULL,
        TRA              BIT            NOT NULL
            CONSTRAINT DF_CT_PHIEUMUON_TRA DEFAULT (0),
        MANVNS           INT            NULL,
        CONSTRAINT PK_CT_PHIEUMUON PRIMARY KEY (MAPHIEU, MASACH),
        CONSTRAINT FK_CT_PHIEUMUON_PHIEUMUON FOREIGN KEY (MAPHIEU)
            REFERENCES dbo.PHIEUMUON (MAPHIEU),
        CONSTRAINT FK_CT_PHIEUMUON_SACH FOREIGN KEY (MASACH)
            REFERENCES dbo.SACH (MASACH),
        CONSTRAINT FK_CT_PHIEUMUON_NHANVIEN FOREIGN KEY (MANVNS)
            REFERENCES dbo.NHANVIEN (MANV),
        CONSTRAINT CK_CT_PHIEUMUON_RETURN_STATE CHECK
        (
            (TRA = 0 AND NGAYTRA IS NULL AND MANVNS IS NULL)
            OR
            (TRA = 1 AND NGAYTRA IS NOT NULL AND MANVNS IS NOT NULL)
        )
    );
END;
GO

/*
    Enforce the borrowing rules stated in the teacher's document:
    - the reader card is active and valid on the borrowing date;
    - a reader holds no more than three unreturned books;
    - a damaged/unusable book cannot be borrowed;
    - one physical book cannot have two active loans;
    - a return cannot predate its loan.

    Locks on the reader and physical-book rows serialize concurrent borrowing
    attempts for the same reader or copy.
*/
CREATE OR ALTER TRIGGER dbo.trg_CT_PHIEUMUON_ValidateAndSync
ON dbo.CT_PHIEUMUON
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @LockedRows INT;

    SELECT @LockedRows = COUNT(*)
    FROM dbo.DOCGIA AS reader WITH (UPDLOCK, HOLDLOCK)
    WHERE reader.MADG IN
    (
        SELECT loan.MADG
        FROM inserted AS detail
        INNER JOIN dbo.PHIEUMUON AS loan ON loan.MAPHIEU = detail.MAPHIEU
    );

    SELECT @LockedRows = COUNT(*)
    FROM dbo.SACH AS book WITH (UPDLOCK, HOLDLOCK)
    WHERE book.MASACH IN
    (
        SELECT MASACH FROM inserted
        UNION
        SELECT MASACH FROM deleted
    );

    IF EXISTS
    (
        SELECT 1
        FROM inserted AS detail
        INNER JOIN dbo.PHIEUMUON AS loan ON loan.MAPHIEU = detail.MAPHIEU
        INNER JOIN dbo.DOCGIA AS reader ON reader.MADG = loan.MADG
        WHERE detail.TRA = 0
          AND
          (
              reader.HOATDONG = 0
              OR reader.NGAYHETHAN < loan.NGAYMUON
              OR reader.NGAYLAMTHE > loan.NGAYMUON
          )
    )
    BEGIN
        ;THROW 50010, 'Reader card must be active and valid on the borrowing date.', 1;
    END;

    IF EXISTS
    (
        SELECT 1
        FROM inserted AS detail
        INNER JOIN dbo.SACH AS book ON book.MASACH = detail.MASACH
        WHERE detail.TRA = 0 AND book.TINHTRANG = 0
    )
    BEGIN
        ;THROW 50011, 'A damaged or unusable book cannot be borrowed.', 1;
    END;

    IF EXISTS
    (
        SELECT detail.MASACH
        FROM dbo.CT_PHIEUMUON AS detail
        WHERE detail.TRA = 0
          AND detail.MASACH IN (SELECT MASACH FROM inserted)
        GROUP BY detail.MASACH
        HAVING COUNT(*) > 1
    )
    BEGIN
        ;THROW 50012, 'A physical book is already on loan.', 1;
    END;

    IF EXISTS
    (
        SELECT active_loan.MADG
        FROM
        (
            SELECT loan.MADG, COUNT(*) AS ActiveBookCount
            FROM dbo.PHIEUMUON AS loan
            INNER JOIN dbo.CT_PHIEUMUON AS detail
                ON detail.MAPHIEU = loan.MAPHIEU
            WHERE detail.TRA = 0
              AND loan.MADG IN
              (
                  SELECT inserted_loan.MADG
                  FROM inserted AS inserted_detail
                  INNER JOIN dbo.PHIEUMUON AS inserted_loan
                      ON inserted_loan.MAPHIEU = inserted_detail.MAPHIEU
              )
            GROUP BY loan.MADG
        ) AS active_loan
        WHERE active_loan.ActiveBookCount > 3
    )
    BEGIN
        ;THROW 50013, 'A reader may hold at most three unreturned books.', 1;
    END;

    IF EXISTS
    (
        SELECT 1
        FROM inserted AS detail
        INNER JOIN dbo.PHIEUMUON AS loan ON loan.MAPHIEU = detail.MAPHIEU
        WHERE detail.TRA = 1 AND detail.NGAYTRA < loan.NGAYMUON
    )
    BEGIN
        ;THROW 50014, 'The return date cannot be earlier than the borrowing date.', 1;
    END;

    ;WITH AffectedBooks AS
    (
        SELECT MASACH FROM inserted
        UNION
        SELECT MASACH FROM deleted
    )
    UPDATE book
    SET CHOMUON = CASE
        WHEN EXISTS
        (
            SELECT 1
            FROM dbo.CT_PHIEUMUON AS detail
            WHERE detail.MASACH = book.MASACH AND detail.TRA = 0
        ) THEN 1 ELSE 0 END
    FROM dbo.SACH AS book
    INNER JOIN AffectedBooks AS affected ON affected.MASACH = book.MASACH;
END;
GO

/* Prevent direct edits from making SACH.CHOMUON disagree with loan details. */
CREATE OR ALTER TRIGGER dbo.trg_SACH_EnforceLoanState
ON dbo.SACH
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS
    (
        SELECT 1
        FROM inserted AS book
        WHERE book.CHOMUON <>
            CASE WHEN EXISTS
            (
                SELECT 1
                FROM dbo.CT_PHIEUMUON AS detail
                WHERE detail.MASACH = book.MASACH AND detail.TRA = 0
            ) THEN 1 ELSE 0 END
    )
    BEGIN
        ;THROW 50015, 'SACH.CHOMUON must match the active loan details.', 1;
    END;
END;
GO

/* 30-day due date and 500 VND per overdue day, as stated in the document. */
CREATE OR ALTER VIEW dbo.v_CHITIET_MUONTRA
AS
SELECT
    loan.MAPHIEU,
    loan.MADG,
    reader.HODG,
    reader.TENDG,
    detail.MASACH,
    book.ISBN,
    title.TENSACH,
    loan.HINHTHUC,
    loan.NGAYMUON,
    DATEADD(DAY, 30, loan.NGAYMUON) AS NGAYHENTRA,
    detail.NGAYTRA,
    detail.TINHTRANGMUON,
    detail.TRA,
    loan.MANV AS MANV_CHOMUON,
    detail.MANVNS AS MANV_NHANSACH,
    CASE
        WHEN DATEDIFF
        (
            DAY,
            DATEADD(DAY, 30, loan.NGAYMUON),
            COALESCE(detail.NGAYTRA, GETDATE())
        ) > 0
        THEN DATEDIFF
        (
            DAY,
            DATEADD(DAY, 30, loan.NGAYMUON),
            COALESCE(detail.NGAYTRA, GETDATE())
        )
        ELSE 0
    END AS SONGAYQUAHAN,
    CONVERT(BIGINT, 500) *
    CASE
        WHEN DATEDIFF
        (
            DAY,
            DATEADD(DAY, 30, loan.NGAYMUON),
            COALESCE(detail.NGAYTRA, GETDATE())
        ) > 0
        THEN DATEDIFF
        (
            DAY,
            DATEADD(DAY, 30, loan.NGAYMUON),
            COALESCE(detail.NGAYTRA, GETDATE())
        )
        ELSE 0
    END AS TIENPHATQUAHAN
FROM dbo.PHIEUMUON AS loan
INNER JOIN dbo.DOCGIA AS reader ON reader.MADG = loan.MADG
INNER JOIN dbo.CT_PHIEUMUON AS detail ON detail.MAPHIEU = loan.MAPHIEU
INNER JOIN dbo.SACH AS book ON book.MASACH = detail.MASACH
INNER JOIN dbo.ISBN AS title ON title.ISBN = book.ISBN;
GO

CREATE OR ALTER VIEW dbo.v_DOCGIA_MUON_QUAHAN
AS
SELECT *
FROM dbo.v_CHITIET_MUONTRA
WHERE TRA = 0 AND SONGAYQUAHAN > 0;
GO

CREATE OR ALTER VIEW dbo.v_ChiTietPhieuMuon_Phat
AS
SELECT 
    v.MAPHIEU,
    v.MADG,
    v.HODG + ' ' + v.TENDG AS HoTenDG,
    r.DIENTHOAI,
    r.EMAILDG,
    v.MASACH,
    v.ISBN,
    v.TENSACH,
    ISNULL(i.GIA, 0) AS GiaBia,
    v.HINHTHUC,
    CASE WHEN v.HINHTHUC = 1 THEN N'Mang về' ELSE N'Tại chỗ' END AS HinhThucStr,
    v.NGAYMUON,
    DATEDIFF(DAY, v.NGAYMUON, COALESCE(v.NGAYTRA, GETDATE())) AS SoNgayDaMuon,
    v.NGAYTRA,
    v.TINHTRANGMUON,
    v.TRA,
    v.MANV_CHOMUON,
    v.MANV_NHANSACH,
    v.SONGAYQUAHAN AS SoNgayTre,
    v.TIENPHATQUAHAN AS TienPhatTre
FROM dbo.v_CHITIET_MUONTRA v
JOIN dbo.DOCGIA r ON v.MADG = r.MADG
JOIN dbo.ISBN i ON v.ISBN = i.ISBN;
GO

CREATE OR ALTER VIEW dbo.v_TANSUAT_SU_DUNG_SACH
AS
SELECT
    title.ISBN,
    title.TENSACH,
    COUNT(detail.MASACH) AS SOLANMUON
FROM dbo.ISBN AS title
LEFT JOIN dbo.SACH AS book ON book.ISBN = title.ISBN
LEFT JOIN dbo.CT_PHIEUMUON AS detail ON detail.MASACH = book.MASACH
GROUP BY title.ISBN, title.TENSACH;
GO
