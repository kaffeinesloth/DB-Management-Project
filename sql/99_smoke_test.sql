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
SELECT N'ALL_DATABASE_SMOKE_TESTS_PASSED' AS Result;
GO
