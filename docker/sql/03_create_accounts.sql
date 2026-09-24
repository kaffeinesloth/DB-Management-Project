USE [master];
GO

IF SUSER_ID(N'nguyen_trong_hoang') IS NULL
BEGIN
    CREATE LOGIN [nguyen_trong_hoang]
        WITH PASSWORD = '$(MANAGER_PASSWORD)',
             CHECK_POLICY = ON,
             CHECK_EXPIRATION = OFF;
END;
GO

IF SUSER_ID(N'tran_thi_mai') IS NULL
BEGIN
    CREATE LOGIN [tran_thi_mai]
        WITH PASSWORD = '$(STAFF_PASSWORD)',
             CHECK_POLICY = ON,
             CHECK_EXPIRATION = OFF;
END;
GO

USE [QLTV];
GO

IF DATABASE_PRINCIPAL_ID(N'1') IS NULL
BEGIN
    CREATE USER [1] FOR LOGIN [nguyen_trong_hoang];
END;
GO

IF DATABASE_PRINCIPAL_ID(N'2') IS NULL
BEGIN
    CREATE USER [2] FOR LOGIN [tran_thi_mai];
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.database_role_members
    WHERE role_principal_id = DATABASE_PRINCIPAL_ID(N'QLTV_MANAGER')
      AND member_principal_id = DATABASE_PRINCIPAL_ID(N'1')
)
BEGIN
    ALTER ROLE [QLTV_MANAGER] ADD MEMBER [1];
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.database_role_members
    WHERE role_principal_id = DATABASE_PRINCIPAL_ID(N'QLTV_STAFF')
      AND member_principal_id = DATABASE_PRINCIPAL_ID(N'2')
)
BEGIN
    ALTER ROLE [QLTV_STAFF] ADD MEMBER [2];
END;
GO

