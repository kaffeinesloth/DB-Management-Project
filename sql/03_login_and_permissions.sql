/*
    Library Management System - application login and permissions

    This script must be executed by sqlcmd with these variables:
      APP_DB_USER
      APP_DB_PASSWORD

    Docker supplies both shared development values from .env or the Compose
    defaults. The application account receives data access only; it cannot
    create objects, administer logins, back up, restore, or control the database.
*/

:on error exit

USE [master];
GO

IF DB_ID(N'LibraryManagement') IS NULL
BEGIN
    ;THROW 50001, 'LibraryManagement does not exist. Run 01_create_tables.sql first.', 1;
END;

DECLARE @LoginName SYSNAME = N'$(APP_DB_USER)';
DECLARE @LoginPassword NVARCHAR(128) = N'$(APP_DB_PASSWORD)';
DECLARE @Command NVARCHAR(MAX);

IF NULLIF(LTRIM(RTRIM(@LoginName)), N'') IS NULL
BEGIN
    ;THROW 50002, 'APP_DB_USER must not be empty.', 1;
END;

IF LEN(@LoginPassword) < 8
BEGIN
    ;THROW 50003, 'APP_DB_PASSWORD must contain at least 8 characters.', 1;
END;

IF EXISTS
(
    SELECT 1
    FROM sys.server_principals
    WHERE name = @LoginName AND type <> 'S'
)
BEGIN
    ;THROW 50004, 'APP_DB_USER already exists but is not a SQL login.', 1;
END;

IF SUSER_ID(@LoginName) IS NULL
BEGIN
    SET @Command =
        N'CREATE LOGIN ' + QUOTENAME(@LoginName)
        + N' WITH PASSWORD = N' + QUOTENAME(@LoginPassword, '''')
        + N', CHECK_POLICY = ON, CHECK_EXPIRATION = OFF,'
        + N' DEFAULT_DATABASE = [LibraryManagement];';
END;
ELSE
BEGIN
    SET @Command =
        N'ALTER LOGIN ' + QUOTENAME(@LoginName)
        + N' WITH PASSWORD = N' + QUOTENAME(@LoginPassword, '''')
        + N', CHECK_POLICY = ON, CHECK_EXPIRATION = OFF,'
        + N' DEFAULT_DATABASE = [LibraryManagement];';
END;

EXEC sys.sp_executesql @Command;
GO

USE [LibraryManagement];
GO

DECLARE @LoginName SYSNAME = N'$(APP_DB_USER)';
DECLARE @Command NVARCHAR(MAX);

IF DATABASE_PRINCIPAL_ID(@LoginName) IS NULL
BEGIN
    SET @Command =
        N'CREATE USER ' + QUOTENAME(@LoginName)
        + N' FOR LOGIN ' + QUOTENAME(@LoginName) + N';';
END;
ELSE
BEGIN
    SET @Command =
        N'ALTER USER ' + QUOTENAME(@LoginName)
        + N' WITH LOGIN = ' + QUOTENAME(@LoginName) + N';';
END;

EXEC sys.sp_executesql @Command;

IF DATABASE_PRINCIPAL_ID(N'library_app_role') IS NULL
BEGIN
    CREATE ROLE [library_app_role] AUTHORIZATION [dbo];
END;

GRANT CONNECT TO [library_app_role];
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::[dbo] TO [library_app_role];

IF NOT EXISTS
(
    SELECT 1
    FROM sys.database_role_members AS membership
    INNER JOIN sys.database_principals AS role_principal
        ON role_principal.principal_id = membership.role_principal_id
    INNER JOIN sys.database_principals AS member_principal
        ON member_principal.principal_id = membership.member_principal_id
    WHERE role_principal.name = N'library_app_role'
      AND member_principal.name = @LoginName
)
BEGIN
    SET @Command =
        N'ALTER ROLE [library_app_role] ADD MEMBER '
        + QUOTENAME(@LoginName) + N';';
    EXEC sys.sp_executesql @Command;
END;

SELECT
    member_principal.name AS database_user,
    role_principal.name AS database_role
FROM sys.database_role_members AS membership
INNER JOIN sys.database_principals AS role_principal
    ON role_principal.principal_id = membership.role_principal_id
INNER JOIN sys.database_principals AS member_principal
    ON member_principal.principal_id = membership.member_principal_id
WHERE role_principal.name = N'library_app_role'
  AND member_principal.name = @LoginName;
GO
