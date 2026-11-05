/*
    Library Management System - backup history VIEW, permissions, and the
    backup / verify / restore workflow.

    Run this file through sqlcmd with:
      ACTION      = SETUP, BACKUP, VERIFY, or RESTORE
      BACKUP_FILE = a filename only, ending in .bak (ignored by SETUP)

    Examples:
      sqlcmd -S localhost -U sa -C -b -v ACTION=SETUP  BACKUP_FILE=LibraryManagement.bak -i 04_backup_and_restore.sql
      sqlcmd -S localhost -U sa -C -b -v ACTION=BACKUP BACKUP_FILE=manual_20261105.bak  -i 04_backup_and_restore.sql

    PART 1 (always runs, idempotent):
      - VIEW dbo.v_LichSuBackup (parameterless query -> VIEW, not a stored procedure)
      - Minimum permissions so login [admin] / user [3] / role QUANLY can
        back up, verify, and restore from the application.

    PART 2 (reference): the exact T-SQL that the Python application
      (backup_and_restore/backup_actions.py) sends to SQL Server.

    PART 3: the sqlcmd maintenance actions used by docker/database-maintenance.sh.

    Docker mounts the persistent backup volume at:
      /var/opt/mssql/backups

    RESTORE replaces LibraryManagement and disconnects its active users. The
    docker/database-maintenance.sh helper requires explicit confirmation first.
*/

:on error exit

/* ============================================================
   PART 1. VIEW dbo.v_LichSuBackup + permissions
   ============================================================ */

USE [LibraryManagement];
GO

/*
    Backup history of the current database (full backups only).

    - position             : backup set number inside the .bak file (Ban 1, 2, 3...)
                             -> used as RESTORE ... WITH FILE = position
    - NgayGioBackup        : backup_finish_date
    - NguoiSaoLuu          : login that ran the backup (user_name)
    - TenBanSaoLuu         : backup set name (BACKUP ... WITH NAME = ...)
    - KichThuocMB          : ROUND(backup_size / 1024.0 / 1024.0, 2)
    - physical_device_name : full path of the .bak file

    Only backup sets of the CURRENT media set of each file are listed. When a
    file is re-formatted (WITH FORMAT, INIT) msdb still keeps the rows of the
    old media set, but those backup sets no longer exist inside the file, so
    they must not be offered for restore.

    Sorting: SQL Server does not allow ORDER BY inside a view unless TOP is
    used (error 1033), and even TOP 100 PERCENT ... ORDER BY does not guarantee
    the order of the outer query. The ordering is therefore applied when the
    view is read:
        SELECT * FROM dbo.v_LichSuBackup ORDER BY NgayGioBackup DESC, position DESC;
*/
CREATE OR ALTER VIEW dbo.v_LichSuBackup
AS
SELECT
    bs.backup_set_id,
    bs.position,
    bs.backup_finish_date                                         AS NgayGioBackup,
    bs.user_name                                                  AS NguoiSaoLuu,
    bs.name                                                       AS TenBanSaoLuu,
    bs.description                                                AS DienGiai,
    CAST(ROUND(bs.backup_size / 1024.0 / 1024.0, 2) AS DECIMAL(18, 2)) AS KichThuocMB,
    bmf.physical_device_name,
    bs.backup_start_date,
    bs.database_name
FROM msdb.dbo.backupset AS bs
INNER JOIN msdb.dbo.backupmediafamily AS bmf
    ON bmf.media_set_id = bs.media_set_id
WHERE bs.database_name = DB_NAME()
  AND bs.type = 'D'                         -- D = full database backup
  AND bs.media_set_id = (
        SELECT MAX(current_media.media_set_id)
        FROM msdb.dbo.backupmediafamily AS current_media
        WHERE current_media.physical_device_name = bmf.physical_device_name
  );
GO

GRANT SELECT ON dbo.v_LichSuBackup TO QUANLY;
GO

-- User [3] (login admin, role QUANLY) may run BACKUP DATABASE on this database.
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'3' AND type = 'S')
    ALTER ROLE [db_backupoperator] ADD MEMBER [3];
GO

USE [master];
GO

-- dbcreator: ALTER DATABASE ... SET SINGLE_USER/MULTI_USER, RESTORE (REPLACE)
-- and RESTORE VERIFYONLY on an existing database.
IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'admin')
    ALTER SERVER ROLE [dbcreator] ADD MEMBER [admin];
GO

USE [msdb];
GO

-- The view reads msdb across databases; cross-database ownership chaining is
-- off, so the caller needs SELECT on the two msdb history tables.
IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'admin')
   AND NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'admin')
    CREATE USER [admin] FOR LOGIN [admin];
GO

IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'admin')
BEGIN
    GRANT SELECT ON dbo.backupset TO [admin];
    GRANT SELECT ON dbo.backupmediafamily TO [admin];
END;
GO

/* ============================================================
   PART 2. Reference: T-SQL executed by the application
   (kept as comments so this file stays safe to re-run)
   ============================================================

   -- 2.1 History (newest first)
   SELECT position, TenBanSaoLuu, NgayGioBackup, KichThuocMB, NguoiSaoLuu, physical_device_name
   FROM dbo.v_LichSuBackup
   WHERE physical_device_name = N'/var/opt/mssql/backups/LibraryManagement.bak'
   ORDER BY NgayGioBackup DESC, position DESC;

   -- 2.2a Backup, append to the file (default, checkbox NOT ticked) -> Ban 1, 2, 3...
   BACKUP DATABASE [LibraryManagement]
       TO DISK = N'/var/opt/mssql/backups/LibraryManagement.bak'
       WITH NOINIT, NAME = N'Ban sao luu truoc khi nhap sach dot 2',
            DESCRIPTION = N'...', CHECKSUM;

   -- 2.2b Backup, reset the file (checkbox ticked) -> old sets erased, restart at Ban 1
   BACKUP DATABASE [LibraryManagement]
       TO DISK = N'/var/opt/mssql/backups/LibraryManagement.bak'
       WITH FORMAT, INIT, MEDIANAME = N'LibraryManagement_Backup',
            NAME = N'...', DESCRIPTION = N'...', CHECKSUM;

   -- 2.3 Verify one backup set
   RESTORE VERIFYONLY
       FROM DISK = N'/var/opt/mssql/backups/LibraryManagement.bak'
       WITH FILE = 2, CHECKSUM;

   -- 2.4 Restore one backup set (run from master on a dedicated connection,
   --     query timeout 300 s)
   USE [master];
   BEGIN TRY
       ALTER DATABASE [LibraryManagement] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;   -- step 1
       RESTORE DATABASE [LibraryManagement]                                          -- step 2
           FROM DISK = N'/var/opt/mssql/backups/LibraryManagement.bak'
           WITH FILE = 2, REPLACE, RECOVERY;
       ALTER DATABASE [LibraryManagement] SET MULTI_USER;                            -- step 3
   END TRY
   BEGIN CATCH
       -- never leave the database stuck in SINGLE_USER
       BEGIN TRY
           IF DB_ID(N'LibraryManagement') IS NOT NULL
               ALTER DATABASE [LibraryManagement] SET MULTI_USER;
       END TRY
       BEGIN CATCH
       END CATCH;
       THROW;
   END CATCH;
*/

/* ============================================================
   PART 3. sqlcmd maintenance actions
   ============================================================ */

USE [master];
GO

DECLARE @Action NVARCHAR(10) = UPPER(N'$(ACTION)');
DECLARE @BackupFile NVARCHAR(255) = N'$(BACKUP_FILE)';
DECLARE @BackupPath NVARCHAR(4000);

IF @Action NOT IN (N'SETUP', N'BACKUP', N'VERIFY', N'RESTORE')
BEGIN
    ;THROW 50020, 'ACTION must be SETUP, BACKUP, VERIFY, or RESTORE.', 1;
END;

IF @Action = N'SETUP'
BEGIN
    SELECT N'BACKUP_SETUP_COMPLETE' AS result;
    RETURN;
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
        BEGIN TRY
            IF DB_ID(N'LibraryManagement') IS NOT NULL
                ALTER DATABASE [LibraryManagement] SET MULTI_USER;
        END TRY
        BEGIN CATCH
        END CATCH;
        THROW;
    END CATCH;
END;
GO
