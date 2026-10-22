/*
    Canonical Project 02 database verification

    The initializer runs this last. Any mismatch makes database-init exit with
    a failure instead of silently giving one team member a different schema.
*/

:on error exit

USE [LibraryManagement];
GO

SET NOCOUNT ON;

DECLARE @ExpectedColumns TABLE
(
    TableName  SYSNAME NOT NULL,
    ColumnName SYSNAME NOT NULL,
    TypeName   SYSNAME NOT NULL,
    MaxLength  SMALLINT NOT NULL,
    IsNullable BIT NOT NULL,
    IsIdentity BIT NOT NULL,
    PRIMARY KEY (TableName, ColumnName)
);

INSERT INTO @ExpectedColumns
    (TableName, ColumnName, TypeName, MaxLength, IsNullable, IsIdentity)
VALUES
    (N'THELOAI', N'MATL', N'char', 5, 0, 0),
    (N'THELOAI', N'THELOAI', N'nvarchar', 100, 0, 0),
    (N'NGONNGU', N'MANGONNGU', N'int', 4, 0, 1),
    (N'NGONNGU', N'NGONNGU', N'nvarchar', 100, 0, 0),
    (N'NGANTU', N'MANGANTU', N'int', 4, 0, 1),
    (N'NGANTU', N'MOTA', N'nvarchar', 100, 1, 0),
    (N'NGANTU', N'KE', N'nvarchar', 200, 0, 0),
    (N'TACGIA', N'MATACGIA', N'int', 4, 0, 1),
    (N'TACGIA', N'HOTENTG', N'nvarchar', 100, 0, 0),
    (N'TACGIA', N'DIACHITG', N'nvarchar', 200, 1, 0),
    (N'TACGIA', N'DIENTHOAITG', N'varchar', 11, 1, 0),
    (N'DOCGIA', N'MADG', N'bigint', 8, 0, 1),
    (N'DOCGIA', N'HODG', N'nvarchar', 100, 0, 0),
    (N'DOCGIA', N'TENDG', N'nvarchar', 24, 0, 0),
    (N'DOCGIA', N'EMAILDG', N'nvarchar', 100, 1, 0),
    (N'DOCGIA', N'SOCMND', N'varchar', 12, 0, 0),
    (N'DOCGIA', N'GIOITINH', N'bit', 1, 1, 0),
    (N'DOCGIA', N'NGAYSINH', N'smalldatetime', 4, 1, 0),
    (N'DOCGIA', N'DIACHI', N'nvarchar', 200, 1, 0),
    (N'DOCGIA', N'DIENTHOAI', N'varchar', 11, 1, 0),
    (N'DOCGIA', N'NGAYLAMTHE', N'smalldatetime', 4, 0, 0),
    (N'DOCGIA', N'NGAYHETHAN', N'smalldatetime', 4, 0, 0),
    (N'DOCGIA', N'HOATDONG', N'bit', 1, 0, 0),
    (N'NHANVIEN', N'MANV', N'int', 4, 0, 1),
    (N'NHANVIEN', N'HONV', N'nvarchar', 100, 0, 0),
    (N'NHANVIEN', N'TENNV', N'nvarchar', 24, 0, 0),
    (N'NHANVIEN', N'GIOITINH', N'bit', 1, 1, 0),
    (N'NHANVIEN', N'DIACHI', N'nvarchar', 200, 1, 0),
    (N'NHANVIEN', N'DIENTHOAI', N'varchar', 11, 1, 0),
    (N'NHANVIEN', N'EMAIL', N'varchar', 50, 1, 0),
    (N'ISBN', N'ISBN', N'char', 10, 0, 0),
    (N'ISBN', N'TENSACH', N'nvarchar', 200, 0, 0),
    (N'ISBN', N'KHOSACH', N'nvarchar', 10, 1, 0),
    (N'ISBN', N'NOIDUNG', N'nvarchar', 600, 1, 0),
    (N'ISBN', N'HINHANHPATH', N'nvarchar', 100, 1, 0),
    (N'ISBN', N'NGAYXUATBAN', N'smalldatetime', 4, 1, 0),
    (N'ISBN', N'LANXUATBAN', N'int', 4, 1, 0),
    (N'ISBN', N'SOTRANG', N'int', 4, 1, 0),
    (N'ISBN', N'GIA', N'bigint', 8, 1, 0),
    (N'ISBN', N'NHAXB', N'nvarchar', 200, 1, 0),
    (N'ISBN', N'MANGONNGU', N'int', 4, 0, 0),
    (N'ISBN', N'MATL', N'char', 5, 0, 0),
    (N'SACH', N'MASACH', N'varchar', 10, 0, 0),
    (N'SACH', N'ISBN', N'char', 10, 0, 0),
    (N'SACH', N'TINHTRANG', N'bit', 1, 0, 0),
    (N'SACH', N'CHOMUON', N'bit', 1, 0, 0),
    (N'SACH', N'MANGANTU', N'int', 4, 0, 0),
    (N'TACGIA_SACH', N'MATACGIA', N'int', 4, 0, 0),
    (N'TACGIA_SACH', N'ISBN', N'char', 10, 0, 0),
    (N'PHIEUMUON', N'MAPHIEU', N'bigint', 8, 0, 1),
    (N'PHIEUMUON', N'MADG', N'bigint', 8, 0, 0),
    (N'PHIEUMUON', N'HINHTHUC', N'bit', 1, 0, 0),
    (N'PHIEUMUON', N'NGAYMUON', N'smalldatetime', 4, 0, 0),
    (N'PHIEUMUON', N'MANV', N'int', 4, 0, 0),
    (N'CT_PHIEUMUON', N'MAPHIEU', N'bigint', 8, 0, 0),
    (N'CT_PHIEUMUON', N'MASACH', N'varchar', 10, 0, 0),
    (N'CT_PHIEUMUON', N'NGAYTRA', N'smalldatetime', 4, 1, 0),
    (N'CT_PHIEUMUON', N'TINHTRANGMUON', N'bit', 1, 0, 0),
    (N'CT_PHIEUMUON', N'TRA', N'bit', 1, 0, 0),
    (N'CT_PHIEUMUON', N'MANVNS', N'int', 4, 1, 0);

IF (SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped = 0) <> 11
BEGIN
    ;THROW 50100, 'The teacher specification requires exactly 11 user tables.', 1;
END;

;WITH ActualColumns AS
(
    SELECT
        table_object.name AS TableName,
        column_object.name AS ColumnName,
        TYPE_NAME(column_object.system_type_id) AS TypeName,
        column_object.max_length AS MaxLength,
        column_object.is_nullable AS IsNullable,
        column_object.is_identity AS IsIdentity
    FROM sys.tables AS table_object
    INNER JOIN sys.schemas AS schema_object
        ON schema_object.schema_id = table_object.schema_id
    INNER JOIN sys.columns AS column_object
        ON column_object.object_id = table_object.object_id
    WHERE schema_object.name = N'dbo'
)
SELECT expected.*
INTO #ColumnProblems
FROM @ExpectedColumns AS expected
LEFT JOIN ActualColumns AS actual
    ON actual.TableName = expected.TableName
   AND actual.ColumnName = expected.ColumnName
WHERE actual.ColumnName IS NULL
   OR actual.TypeName <> expected.TypeName
   OR actual.MaxLength <> expected.MaxLength
   OR actual.IsNullable <> expected.IsNullable
   OR actual.IsIdentity <> expected.IsIdentity;

IF EXISTS (SELECT 1 FROM #ColumnProblems)
BEGIN
    SELECT N'Missing or mismatched required column' AS Problem, *
    FROM #ColumnProblems
    ORDER BY TableName, ColumnName;
    ;THROW 50101, 'The database columns do not match the canonical schema.', 1;
END;

IF
(
    SELECT COUNT(*)
    FROM sys.columns AS column_object
    INNER JOIN sys.tables AS table_object
        ON table_object.object_id = column_object.object_id
    INNER JOIN sys.schemas AS schema_object
        ON schema_object.schema_id = table_object.schema_id
    WHERE schema_object.name = N'dbo'
) <> (SELECT COUNT(*) FROM @ExpectedColumns)
BEGIN
    ;THROW 50102, 'The 11 required tables contain unexpected extra columns.', 1;
END;

DECLARE @RequiredConstraints TABLE (ObjectName SYSNAME PRIMARY KEY);
INSERT INTO @RequiredConstraints (ObjectName)
VALUES
    (N'PK_THELOAI'), (N'PK_NGONNGU'), (N'PK_NGANTU'),
    (N'PK_TACGIA'), (N'PK_DOCGIA'), (N'PK_NHANVIEN'),
    (N'PK_ISBN'), (N'PK_SACH'), (N'PK_TACGIA_SACH'),
    (N'PK_PHIEUMUON'), (N'PK_CT_PHIEUMUON'),
    (N'FK_ISBN_NGONNGU'), (N'FK_ISBN_THELOAI'),
    (N'FK_SACH_ISBN'), (N'FK_SACH_NGANTU'),
    (N'FK_TACGIA_SACH_TACGIA'), (N'FK_TACGIA_SACH_ISBN'),
    (N'FK_PHIEUMUON_DOCGIA'), (N'FK_PHIEUMUON_NHANVIEN'),
    (N'FK_CT_PHIEUMUON_PHIEUMUON'), (N'FK_CT_PHIEUMUON_SACH'),
    (N'FK_CT_PHIEUMUON_NHANVIEN'),
    (N'CK_DOCGIA_NGAYHETHAN'), (N'CK_ISBN_LANXUATBAN'),
    (N'CK_ISBN_SOTRANG'), (N'CK_ISBN_GIA'),
    (N'CK_CT_PHIEUMUON_RETURN_STATE');

IF EXISTS
(
    SELECT 1
    FROM @RequiredConstraints AS required_object
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM sys.objects AS database_object
        WHERE database_object.name = required_object.ObjectName
          AND database_object.schema_id = SCHEMA_ID(N'dbo')
    )
)
BEGIN
    SELECT required_object.ObjectName AS MissingConstraint
    FROM @RequiredConstraints AS required_object
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM sys.objects AS database_object
        WHERE database_object.name = required_object.ObjectName
          AND database_object.schema_id = SCHEMA_ID(N'dbo')
    );
    ;THROW 50103, 'A required key or check constraint is missing.', 1;
END;

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.DOCGIA')
      AND name = N'UX_DOCGIA_SOCMND_ACTIVE'
      AND is_unique = 1
      AND has_filter = 1
)
BEGIN
    ;THROW 50104, 'The active-card citizen-ID rule is missing.', 1;
END;

IF OBJECT_ID(N'dbo.trg_CT_PHIEUMUON_ValidateAndSync', N'TR') IS NULL
   OR OBJECT_ID(N'dbo.trg_SACH_EnforceLoanState', N'TR') IS NULL
BEGIN
    ;THROW 50105, 'A borrowing consistency trigger is missing.', 1;
END;

IF OBJECT_ID(N'dbo.v_CHITIET_MUONTRA', N'V') IS NULL
   OR OBJECT_ID(N'dbo.v_DOCGIA_MUON_QUAHAN', N'V') IS NULL
   OR OBJECT_ID(N'dbo.v_TANSUAT_SU_DUNG_SACH', N'V') IS NULL
BEGIN
    ;THROW 50106, 'A teacher-required borrowing report view is missing.', 1;
END;

IF DATABASE_PRINCIPAL_ID(N'library_app_role') IS NULL
BEGIN
    ;THROW 50107, 'The shared application database role is missing.', 1;
END;

SELECT
    N'DATABASE_CONTRACT_OK' AS Result,
    DB_NAME() AS DatabaseName,
    COUNT(DISTINCT TableName) AS RequiredTableCount,
    COUNT(*) AS RequiredColumnCount
FROM @ExpectedColumns;
GO
