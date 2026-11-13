/*
    SSMS classroom demo for the Python login form.

    Connect in SSMS with:
      Server name: localhost,1433
      Authentication: SQL Server Authentication
      Login: admin (or nv_huong / nv_long / nv_nam)
      Password: 123456
      Options > Connection Properties > Trust server certificate: checked
*/

USE [LibraryManagement];
GO

-- 1) The four SQL Server logins used by the form.
SELECT
    sp.name AS LoginName,
    sp.type_desc AS LoginType,
    sp.is_disabled AS IsDisabled,
    sp.default_database_name AS DefaultDatabase
FROM sys.server_principals AS sp
WHERE sp.name IN (N'admin', N'nv_huong', N'nv_long', N'nv_nam')
ORDER BY sp.name;

-- 2) Login -> numbered database user -> application role.
SELECT
    SUSER_SNAME(dp.sid) AS LoginName,
    dp.name AS DatabaseUser,
    role_dp.name AS DatabaseRole
FROM sys.database_principals AS dp
JOIN sys.database_role_members AS drm
  ON drm.member_principal_id = dp.principal_id
JOIN sys.database_principals AS role_dp
  ON role_dp.principal_id = drm.role_principal_id
WHERE dp.name IN (N'1', N'2', N'3', N'4')
ORDER BY dp.name;

-- 3) Run this while connected as one of the four users.
SELECT
    ORIGINAL_LOGIN() AS ConnectedLogin,
    USER_NAME() AS DatabaseUser;
EXEC dbo.sp_LayThongTinHienTai;
GO

-- 4) Account status used by the manager screen.
EXEC dbo.sp_DanhSachTaiKhoanNhanVien;
GO

-- 5) Verify that account administration is encapsulated in signed procedures.
SELECT
    procedure_name = OBJECT_SCHEMA_NAME(cp.major_id) + N'.' + OBJECT_NAME(cp.major_id),
    certificate_name = cert.name
FROM sys.crypt_properties AS cp
JOIN sys.certificates AS cert
  ON cert.thumbprint = cp.thumbprint
WHERE cp.major_id IN
(
    OBJECT_ID(N'dbo.sp_TaoTaiKhoanNhanVien'),
    OBJECT_ID(N'dbo.sp_XoaTaiKhoanNhanVien')
);
GO
