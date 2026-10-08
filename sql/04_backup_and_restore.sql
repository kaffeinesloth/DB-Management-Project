/*
    Library Management System - backup, verification, and restore

    Run this file through sqlcmd with:
      ACTION      = BACKUP, VERIFY, or RESTORE
      BACKUP_FILE = a filename only, ending in .bak

    Docker mounts the persistent backup volume at:
      /var/opt/mssql/backups

    RESTORE replaces LibraryManagement and disconnects its active users. The
    docker/database-maintenance.sh helper requires explicit confirmation first.
*/

:on error exit

USE [master];
GO

DECLARE @Action NVARCHAR(10) = UPPER(N'$(ACTION)');
DECLARE @BackupFile NVARCHAR(255) = N'$(BACKUP_FILE)';
DECLARE @BackupPath NVARCHAR(4000);

IF @Action NOT IN (N'BACKUP', N'VERIFY', N'RESTORE')
BEGIN
    ;THROW 50020, 'ACTION must be BACKUP, VERIFY, or RESTORE.', 1;
END;

IF NULLIF(LTRIM(RTRIM(@BackupFile)), N'') IS NULL
BEGIN
    ;THROW 50021, 'BACKUP_FILE must not be empty.', 1;
END;

IF @BackupFile LIKE N'%[^-A-Za-z0-9._]%' COLLATE Latin1_General_100_BIN2
   OR @BackupFile LIKE N'%..%'
   OR RIGHT(LOWER(@BackupFile), 4) <> N'.bak'
BEGIN
    ;THROW 50022, 'BACKUP_FILE must be a safe .bak filename without a directory path.', 1;
END;

SET @BackupPath = N'/var/opt/mssql/backups/' + @BackupFile;

IF @Action = N'BACKUP'
BEGIN
    IF DB_ID(N'LibraryManagement') IS NULL
    BEGIN
        ;THROW 50023, 'LibraryManagement does not exist.', 1;
    END;

    BACKUP DATABASE [LibraryManagement]
        TO DISK = @BackupPath
        WITH COPY_ONLY, INIT, CHECKSUM, COMPRESSION, STATS = 10;

    RESTORE VERIFYONLY
        FROM DISK = @BackupPath
        WITH CHECKSUM;

    SELECT
        N'BACKUP_AND_VERIFY_COMPLETE' AS result,
        @BackupFile AS backup_file,
        @BackupPath AS container_path;
END;
ELSE IF @Action = N'VERIFY'
BEGIN
    RESTORE VERIFYONLY
        FROM DISK = @BackupPath
        WITH CHECKSUM;

    RESTORE HEADERONLY
        FROM DISK = @BackupPath;
END;
ELSE
BEGIN
    BEGIN TRY
        IF DB_ID(N'LibraryManagement') IS NOT NULL
        BEGIN
            ALTER DATABASE [LibraryManagement]
                SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
        END;

        RESTORE DATABASE [LibraryManagement]
            FROM DISK = @BackupPath
            WITH REPLACE, RECOVERY, CHECKSUM, STATS = 10;

        ALTER DATABASE [LibraryManagement] SET MULTI_USER;

        SELECT
            N'RESTORE_COMPLETE' AS result,
            @BackupFile AS backup_file,
            @BackupPath AS container_path;
    END TRY
    BEGIN CATCH
        IF DB_ID(N'LibraryManagement') IS NOT NULL
        BEGIN
            ALTER DATABASE [LibraryManagement] SET MULTI_USER;
        END;
        THROW;
    END CATCH;
END;
GO
