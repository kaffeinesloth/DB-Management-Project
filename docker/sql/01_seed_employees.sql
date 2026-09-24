USE [QLTV];
GO

IF EXISTS (SELECT 1 FROM dbo.NHANVIEN)
BEGIN
    THROW 51030, 'NHANVIEN is not empty; Docker seed was not applied.', 1;
END;
GO

INSERT INTO dbo.NHANVIEN
    (HONV, TENNV, GIOITINH, DIACHI, DIENTHOAI, EMAIL)
VALUES
    (N'Nguyễn Trọng', N'Hoàng', 1, N'Hà Nội',
     '0987654321', 'admin@qltv.com'),
    (N'Trần Thị', N'Mai', 0, N'Hà Nội',
     '0976543210', 'mai.tt@qltv.com');
GO

IF (SELECT COUNT(*) FROM dbo.NHANVIEN WHERE MANV IN (1, 2)) <> 2
BEGIN
    THROW 51031, 'Expected employee IDs 1 and 2 were not created.', 1;
END;
GO

