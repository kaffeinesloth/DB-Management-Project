USE [QLTV];
GO

IF EXISTS
(
    SELECT 1
    FROM sys.extended_properties
    WHERE class = 0
      AND name = N'QLTV_DOCKER_SETUP_VERSION'
)
BEGIN
    EXEC sys.sp_updateextendedproperty
        @name = N'QLTV_DOCKER_SETUP_VERSION',
        @value = N'1';
END;
ELSE
BEGIN
    EXEC sys.sp_addextendedproperty
        @name = N'QLTV_DOCKER_SETUP_VERSION',
        @value = N'1';
END;
GO

