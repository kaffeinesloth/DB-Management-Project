/*
    One-time repair for the development database where SQL Server identity
    caching caused MANV to jump from 5 to 2002 after container restarts.

    The script is deliberately narrow and rerunnable. It only remaps the two
    observed employees when both source IDs exist and target IDs 6/7 are free.
    Their SQL database users are renamed with them so authentication continues
    to enforce database-user name = MANV.
*/

:on error exit

USE [LibraryManagement];
GO

SET XACT_ABORT ON;

IF EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE MANV = 2002)
   AND EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE MANV = 2003)
   AND NOT EXISTS (SELECT 1 FROM dbo.NHANVIEN WHERE MANV IN (6, 7))
BEGIN
    BEGIN TRANSACTION;

    DECLARE @EmployeeIdMap TABLE
    (
        OldMANV INT PRIMARY KEY,
        NewMANV INT UNIQUE NOT NULL
    );
    INSERT INTO @EmployeeIdMap (OldMANV, NewMANV)
    VALUES (2002, 6), (2003, 7);

    SET IDENTITY_INSERT dbo.NHANVIEN ON;
    INSERT INTO dbo.NHANVIEN
        (MANV, HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL)
    SELECT
        id_map.NewMANV, employee.HONV, employee.TENNV, employee.GIOITINH,
        employee.DIACHI, employee.DIENTHOAI, employee.EMAIL
    FROM dbo.NHANVIEN AS employee
    JOIN @EmployeeIdMap AS id_map ON id_map.OldMANV = employee.MANV;
    SET IDENTITY_INSERT dbo.NHANVIEN OFF;

    UPDATE loan_record
    SET MANV = id_map.NewMANV
    FROM dbo.PHIEUMUON AS loan_record
    JOIN @EmployeeIdMap AS id_map ON id_map.OldMANV = loan_record.MANV;

    UPDATE return_record
    SET MANVNS = id_map.NewMANV
    FROM dbo.CT_PHIEUMUON AS return_record
    JOIN @EmployeeIdMap AS id_map ON id_map.OldMANV = return_record.MANVNS;

    DELETE employee
    FROM dbo.NHANVIEN AS employee
    JOIN @EmployeeIdMap AS id_map ON id_map.OldMANV = employee.MANV;

    IF DATABASE_PRINCIPAL_ID(N'2002') IS NOT NULL
       AND DATABASE_PRINCIPAL_ID(N'6') IS NULL
        ALTER USER [2002] WITH NAME = [6];

    IF DATABASE_PRINCIPAL_ID(N'2003') IS NOT NULL
       AND DATABASE_PRINCIPAL_ID(N'7') IS NULL
        ALTER USER [2003] WITH NAME = [7];

    DBCC CHECKIDENT (N'dbo.NHANVIEN', RESEED, 7) WITH NO_INFOMSGS;
    COMMIT TRANSACTION;
END;
GO

SELECT MANV, CONCAT(RTRIM(HONV), N' ', RTRIM(TENNV)) AS HOTEN
FROM dbo.NHANVIEN
ORDER BY MANV;
GO
