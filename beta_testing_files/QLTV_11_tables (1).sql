/* ============================================================
   DE 1 - QUAN LY THU VIEN
   Microsoft SQL Server / SSMS
   Tao database va 11 bang cho de Quan ly Thu vien (da bo SACH_DIENTU).

   Luu y chuan hoa de tao FK hop le:
   - CT_PHIEUMUON.MASACH dung VARCHAR(10) de trung voi SACH.MASACH.
   - NHAXB va NGANTU.KE duoc giu la cot thong tin vi de khong co
     bang NHAXUATBAN/KE trong danh sach bang cua de.
   - Cac cot van ban dung NVARCHAR de luu Unicode tieng Viet.
   ============================================================ */

USE master;
GO

IF DB_ID(N'QLTV') IS NULL
BEGIN
    CREATE DATABASE QLTV;
END;
GO

USE QLTV;
GO

/* ------------------------------------------------------------
   RESET (de script co the chay lai khi lam bai / thu nghiem)
   CANH BAO: cac lenh DROP ben duoi se xoa bang va du lieu cu.
   ------------------------------------------------------------ */
DROP TABLE IF EXISTS dbo.CT_PHIEUMUON;
DROP TABLE IF EXISTS dbo.PHIEUMUON;
DROP TABLE IF EXISTS dbo.TACGIA_SACH;
DROP TABLE IF EXISTS dbo.SACH;
DROP TABLE IF EXISTS dbo.ISBN;
DROP TABLE IF EXISTS dbo.NHANVIEN;
DROP TABLE IF EXISTS dbo.DOCGIA;
DROP TABLE IF EXISTS dbo.TACGIA;
DROP TABLE IF EXISTS dbo.NGANTU;
DROP TABLE IF EXISTS dbo.NGONNGU;
DROP TABLE IF EXISTS dbo.THELOAI;
GO

/* ============================================================
   1. THELOAI
   ============================================================ */
CREATE TABLE dbo.THELOAI
(
    MATL       CHAR(5)       NOT NULL,
    THELOAI    NVARCHAR(50)  NOT NULL,

    CONSTRAINT PK_THELOAI PRIMARY KEY (MATL),
    CONSTRAINT UQ_THELOAI_TEN UNIQUE (THELOAI)
);
GO

/* ============================================================
   2. NGONNGU
   ============================================================ */
CREATE TABLE dbo.NGONNGU
(
    MANGONNGU  INT IDENTITY(1,1) NOT NULL,
    NGONNGU    NVARCHAR(50)      NOT NULL,

    CONSTRAINT PK_NGONNGU PRIMARY KEY (MANGONNGU),
    CONSTRAINT UQ_NGONNGU_TEN UNIQUE (NGONNGU)
);
GO

/* ============================================================
   3. NGANTU
   ============================================================ */
CREATE TABLE dbo.NGANTU
(
    MANGANTU   INT IDENTITY(1,1) NOT NULL,
    MOTA       NVARCHAR(50)      NULL,
    KE         NVARCHAR(100)     NULL,

    CONSTRAINT PK_NGANTU PRIMARY KEY (MANGANTU)
);
GO

/* ============================================================
   4. TACGIA
   ============================================================ */
CREATE TABLE dbo.TACGIA
(
    MATACGIA       INT IDENTITY(1,1) NOT NULL,
    HOTENTG        NVARCHAR(50)      NOT NULL,
    DIACHITG       NVARCHAR(100)     NULL,
    DIENTHOAITG    VARCHAR(11)       NULL,

    CONSTRAINT PK_TACGIA PRIMARY KEY (MATACGIA)
);
GO

/* ============================================================
   5. DOCGIA
   ============================================================ */
CREATE TABLE dbo.DOCGIA
(
    MADG        BIGINT IDENTITY(1,1) NOT NULL,
    HODG        NVARCHAR(50)         NOT NULL,
    TENDG       NVARCHAR(12)         NOT NULL,
    EMAILDG     NVARCHAR(50)         NULL,
    SOCMND      VARCHAR(12)          NULL,
    GIOITINH    BIT                  NULL,
    NGAYSINH    SMALLDATETIME        NULL,
    DIACHI      NVARCHAR(100)        NULL,
    DIENTHOAI   VARCHAR(11)          NULL,
    NGAYLAMTHE  SMALLDATETIME        NOT NULL
                CONSTRAINT DF_DOCGIA_NGAYLAMTHE DEFAULT (GETDATE()),
    NGAYHETHAN  SMALLDATETIME        NULL,
    HOATDONG    BIT                  NOT NULL
                CONSTRAINT DF_DOCGIA_HOATDONG DEFAULT (1),

    CONSTRAINT PK_DOCGIA PRIMARY KEY (MADG),
    CONSTRAINT UQ_DOCGIA_EMAIL UNIQUE (EMAILDG),
    CONSTRAINT UQ_DOCGIA_SOCMND UNIQUE (SOCMND),
    CONSTRAINT CK_DOCGIA_HANTHE CHECK
    (
        NGAYHETHAN IS NULL OR NGAYHETHAN >= NGAYLAMTHE
    )
);
GO

/* ============================================================
   6. NHANVIEN
   ============================================================ */
CREATE TABLE dbo.NHANVIEN
(
    MANV        INT IDENTITY(1,1) NOT NULL,
    HONV        NVARCHAR(50)      NOT NULL,
    TENNV       NVARCHAR(12)      NOT NULL,
    GIOITINH    BIT               NULL,
    DIACHI      NVARCHAR(100)     NULL,
    DIENTHOAI   VARCHAR(11)       NULL,
    EMAIL       VARCHAR(50)       NULL,

    CONSTRAINT PK_NHANVIEN PRIMARY KEY (MANV),
    CONSTRAINT UQ_NHANVIEN_EMAIL UNIQUE (EMAIL)
);
GO

/* ============================================================
   7. ISBN - dau sach
   ============================================================ */
CREATE TABLE dbo.ISBN
(
    ISBN          CHAR(10)       NOT NULL,
    TENSACH       NVARCHAR(100)  NOT NULL,
    KHOSACH       NVARCHAR(5)    NULL,
    NOIDUNG       NVARCHAR(300)  NULL,
    SOTRANG       INT            NULL,
    GIA           BIGINT         NULL,
    HINHANHPATH   NVARCHAR(50)   NULL,
    NGAYXUATBAN   SMALLDATETIME  NULL,
    LANXUATBAN    INT            NULL,
    NHAXB         NVARCHAR(100)  NULL,
    MANGONNGU     INT            NULL,
    MATL          CHAR(5)        NULL,

    CONSTRAINT PK_ISBN PRIMARY KEY (ISBN),

    CONSTRAINT FK_ISBN_NGONNGU
        FOREIGN KEY (MANGONNGU)
        REFERENCES dbo.NGONNGU(MANGONNGU),

    CONSTRAINT FK_ISBN_THELOAI
        FOREIGN KEY (MATL)
        REFERENCES dbo.THELOAI(MATL),

    CONSTRAINT CK_ISBN_SOTRANG CHECK (SOTRANG IS NULL OR SOTRANG > 0),
    CONSTRAINT CK_ISBN_GIA CHECK (GIA IS NULL OR GIA >= 0),
    CONSTRAINT CK_ISBN_LANXUATBAN CHECK (LANXUATBAN IS NULL OR LANXUATBAN > 0)
);
GO

/* ============================================================
   8. SACH - tung cuon sach vat ly
   ============================================================ */
CREATE TABLE dbo.SACH
(
    MASACH      VARCHAR(10)  NOT NULL,
    ISBN        CHAR(10)     NOT NULL,
    TINHTRANG   BIT          NOT NULL
                CONSTRAINT DF_SACH_TINHTRANG DEFAULT (1),
    CHOMUON     BIT          NOT NULL
                CONSTRAINT DF_SACH_CHOMUON DEFAULT (0),
    MANGANTU    INT          NULL,

    CONSTRAINT PK_SACH PRIMARY KEY (MASACH),

    CONSTRAINT FK_SACH_ISBN
        FOREIGN KEY (ISBN)
        REFERENCES dbo.ISBN(ISBN),

    CONSTRAINT FK_SACH_NGANTU
        FOREIGN KEY (MANGANTU)
        REFERENCES dbo.NGANTU(MANGANTU)
);
GO

/* ============================================================
   9. TACGIA_SACH - quan he N-N giua TACGIA va ISBN
   ============================================================ */
CREATE TABLE dbo.TACGIA_SACH
(
    MATACGIA   INT       NOT NULL,
    ISBN       CHAR(10)  NOT NULL,

    CONSTRAINT PK_TACGIA_SACH PRIMARY KEY (MATACGIA, ISBN),

    CONSTRAINT FK_TACGIA_SACH_TACGIA
        FOREIGN KEY (MATACGIA)
        REFERENCES dbo.TACGIA(MATACGIA),

    CONSTRAINT FK_TACGIA_SACH_ISBN
        FOREIGN KEY (ISBN)
        REFERENCES dbo.ISBN(ISBN)
);
GO

/* ============================================================
   10. PHIEUMUON
   ============================================================ */
CREATE TABLE dbo.PHIEUMUON
(
    MAPHIEU    BIGINT IDENTITY(1,1) NOT NULL,
    MADG       BIGINT                NOT NULL,
    HINHTHUC   BIT                   NOT NULL,
    NGAYMUON   SMALLDATETIME         NOT NULL
               CONSTRAINT DF_PHIEUMUON_NGAYMUON DEFAULT (GETDATE()),
    MANV       INT                   NOT NULL,

    CONSTRAINT PK_PHIEUMUON PRIMARY KEY (MAPHIEU),

    CONSTRAINT FK_PHIEUMUON_DOCGIA
        FOREIGN KEY (MADG)
        REFERENCES dbo.DOCGIA(MADG),

    CONSTRAINT FK_PHIEUMUON_NHANVIEN
        FOREIGN KEY (MANV)
        REFERENCES dbo.NHANVIEN(MANV)
);
GO

/* ============================================================
   11. CT_PHIEUMUON
   ============================================================ */
CREATE TABLE dbo.CT_PHIEUMUON
(
    MAPHIEU         BIGINT         NOT NULL,
    MASACH          VARCHAR(10)    NOT NULL,
    NGAYTRA         SMALLDATETIME  NULL,
    TINHTRANGMUON   BIT            NOT NULL,
    TRA              BIT            NOT NULL
                     CONSTRAINT DF_CT_PHIEUMUON_TRA DEFAULT (0),
    MANVNS           INT            NULL,

    CONSTRAINT PK_CT_PHIEUMUON PRIMARY KEY (MAPHIEU, MASACH),

    CONSTRAINT FK_CT_PHIEUMUON_PHIEUMUON
        FOREIGN KEY (MAPHIEU)
        REFERENCES dbo.PHIEUMUON(MAPHIEU),

    CONSTRAINT FK_CT_PHIEUMUON_SACH
        FOREIGN KEY (MASACH)
        REFERENCES dbo.SACH(MASACH),

    CONSTRAINT FK_CT_PHIEUMUON_NHANVIEN
        FOREIGN KEY (MANVNS)
        REFERENCES dbo.NHANVIEN(MANV)
);
GO

/* ============================================================
   INDEXES phuc vu cac khoa ngoai / tra cuu thuong dung
   ============================================================ */
CREATE INDEX IX_ISBN_MATL              ON dbo.ISBN(MATL);
CREATE INDEX IX_ISBN_MANGONNGU         ON dbo.ISBN(MANGONNGU);
CREATE INDEX IX_SACH_ISBN              ON dbo.SACH(ISBN);
CREATE INDEX IX_SACH_MANGANTU          ON dbo.SACH(MANGANTU);
CREATE INDEX IX_PHIEUMUON_MADG         ON dbo.PHIEUMUON(MADG);
CREATE INDEX IX_PHIEUMUON_MANV         ON dbo.PHIEUMUON(MANV);
CREATE INDEX IX_CT_PHIEUMUON_MASACH    ON dbo.CT_PHIEUMUON(MASACH);
CREATE INDEX IX_CT_PHIEUMUON_MANVNS    ON dbo.CT_PHIEUMUON(MANVNS);
GO

/* Kiem tra 11 bang vua tao */
SELECT
    s.name AS SchemaName,
    t.name AS TableName
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
ORDER BY t.name;
GO
