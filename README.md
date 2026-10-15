# HỆ THỐNG QUẢN LÝ THƯ VIỆN (QLTV)
> Đồ án môn học: Hệ Quản Trị Cơ Sở Dữ Liệu  
> Đề tài: Đề 04 - Quản Lý Thư Viện (Chuẩn 11 Bảng theo đặc tả đề bài)  
> Kiến trúc: 2-Tier Layered Architecture (Python CustomTkinter Desktop GUI + Microsoft SQL Server)

---

## 1. GIỚI THIỆU ĐỒ ÁN

QLTV là phần mềm quản lý thư viện máy tính để bàn (Desktop Application) được xây dựng trên ngôn ngữ Python kết hợp giao diện hiện đại CustomTkinter (Dark Mode) và hệ quản trị cơ sở dữ liệu Microsoft SQL Server.

Hệ thống được thiết kế **tuân thủ nghiêm ngặt 100% cấu trúc 11 bảng và các cột của đề bài môn học**, đồng thời áp dụng tối đa các kỹ thuật chuyên sâu của Hệ Quản Trị Cơ Sở Dữ Liệu:
* **Trigger tự động đồng bộ** trạng thái sách (`SACH.CHOMUON`) khi mượn/trả ở cấp CSDL.
* **Filtered Unique Index** kiểm soát tính duy nhất của CMND/Email trên các thẻ đang hoạt động (`HOATDONG = 1`), cho phép cấp lại mã thẻ mới khi mất thẻ mà không gây lỗi trùng lặp.
* **View tính toán phái sinh thời gian thực (Chuẩn hóa 3NF)**: Tự động tính số ngày trễ hạn và tiền phạt (500 VNĐ/ngày) mà không cần thêm cột dư thừa vào bảng vật lý.
* **Bảo mật & Phân quyền RBAC:** Phân cấp quyền hạn rõ ràng giữa Ban Quản Lý (`QUANLY`) và Tổ Phục Vụ Bạn Đọc (`THUTHU`) theo đúng quy chế nghiệp vụ thư viện, xóa bỏ hoàn toàn hardcode mật khẩu quản trị.

---

## 2. CÔNG NGHỆ SỬ DỤNG

* Ngôn ngữ: Python 3.10+
* Giao diện (GUI): CustomTkinter, Tkinter (Dark Theme hiện đại #1E2229, #242830)
* Hệ quản trị CSDL: Microsoft SQL Server (SQL Express / Local Instance)
* Thư viện kết nối CSDL: pyodbc (Hỗ trợ ODBC Driver 18 & 17 for SQL Server)
* Đối tượng CSDL nâng cao: SQL Server Logins, DB Roles, Filtered Indexes, Views, Triggers, Stored Procedures.

---

## 3. CHỨC NĂNG CHÍNH & NGUYÊN LÝ THIẾT KẾ CSDL

### 3.1. Đăng Nhập & Phân Quyền Bảo Mật (login.py & db.py)
* Xác thực tài khoản trực tiếp bằng SQL Server Login (UID / PWD).
* Không lưu mật khẩu plain-text, không hardcode tài khoản quản trị `sa`.
* Tự động nhận diện Mã nhân viên (MANV), Họ tên và Nhóm quyền (`QUANLY` / `THUTHU`) qua Stored Procedure `sp_LayThongTinHienTai`.
* Giao diện tự động thích ứng theo Role: Tự động ẩn các tính năng quản trị kho/sách đối với Thủ thư.

### 3.2. Quản Lý Độc Giả & Thẻ Thư Viện (ui/tabs/tab_docgia.py)
* CRUD Độc giả: Thêm mới, tra cứu đa tiêu chí (Tên, CMND/CCCD, SĐT, Email).
* Nghiệp vụ mất thẻ: Khóa thẻ cũ (`HOATDONG = 0`) và cấp thẻ mới với `MADG` mới. Filtered Index `UQ_DOCGIA_SOCMND_ACTIVE` đảm bảo cùng số CMND/CCCD không bị lỗi vi phạm khóa duy nhất.
* Thời hạn thẻ: Tự động tính ngày làm thẻ và ngày hết hạn. Hỗ trợ gia hạn thẻ (+12 tháng), khóa / mở khóa thẻ.

### 3.3. Quản Lý Sách & Kho (ui/tabs/tab_sach.py)
* Quản lý Đầu Sách (`ISBN`) và Cuốn Sách Vật Lý (`SACH`) gắn với vị trí Ngăn tủ / Kệ (`NGANTU`).
* Kiểm kê kho: Báo hỏng (`TINHTRANG = 0`) hoặc khôi phục sách tốt (`TINHTRANG = 1`).
* Quyền hạn rõ ràng: Chỉ tài khoản Quản lý (`QUANLY`) mới có quyền nhập đầu sách mới, thêm bản sao vật lý và thanh lý sách.

### 3.4. Quản Lý Mượn / Trả Sách & Xử Phạt (ui/tabs/tab_muontra.py)
* Ràng buộc mượn sách:
  - Thẻ độc giả phải còn hạn (`NGAYHETHAN >= GETDATE()`) và đang hoạt động (`HOATDONG = 1`).
  - Độc giả không được giữ quá 3 cuốn sách chưa trả.
  - Sách mượn phải sẵn sàng (`CHOMUON = 0, TINHTRANG = 1`).
  - Lập phiếu mượn thực hiện an toàn trong 1 SQL Transaction kèm Atomic Lock chống Race Condition.
* Xử lý trả sách & Tính phạt:
  - Trigger `trg_DongBoTrangThaiSach` tự động trả trạng thái sách về kho (`CHOMUON = 0`).
  - Tính phạt trễ hạn: Mang về quá 30 ngày -> Phạt (Số ngày trễ) * 500 VNĐ.
  - Phạt hư hỏng: Đền bù 50% giá bìa.
  - Báo mất sách: Bồi thường 100% giá bìa.

### 3.5. Báo Cáo Thống Kê (ui/tabs/tab_thongke.py)
* Sử dụng View `v_ChiTietPhieuMuon_Phat` để đo lường KPI thời gian thực:
  - Tổng số Đầu sách, Cuốn sách, Sách đang cho mượn, Độc giả hoạt động.
  - Danh sách độc giả đang giữ sách quá hạn kèm số tiền phạt dự kiến.
  - Thống kê tần suất mượn sách theo từng đầu sách (Top mượn nhiều nhất / ít nhất).

---

## 4. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
DB-Management-Project/
├── dao/                         # Data Access Objects (Tầng truy vấn CSDL)
│   ├── __init__.py
│   ├── docgia_dao.py            # DAO Quản lý độc giả & thẻ
│   ├── sach_dao.py              # DAO Quản lý ISBN, Sách vật lý, Ngăn tủ
│   ├── muontra_dao.py           # DAO Quản lý Mượn/Trả sách & Tính phạt
│   └── thongke_dao.py           # DAO Thống kê KPI & Báo cáo
├── ui/                          # User Interface (Tầng giao diện CustomTkinter)
│   ├── __init__.py
│   ├── ctk_patch.py             # Patch hỗ trợ placeholder cho CTkEntry
│   ├── main_dashboard.py        # Cửa sổ chính & Sidebar điều hướng
│   └── tabs/
│       ├── __init__.py
│       ├── tab_docgia.py        # Giao diện Quản lý Độc giả
│       ├── tab_sach.py          # Giao diện Quản lý Sách & Kho (Có RBAC)
│       ├── tab_muontra.py       # Giao diện Mượn/Trả sách & Xử phạt
│       └── tab_thongke.py       # Giao diện Báo cáo Thống kê
├── db.py                        # Quản lý kết nối pyodbc & Phiên đăng nhập
├── login.py                     # Màn hình Đăng nhập (SQL Server Authentication)
├── QLTV_11_tables (1).sql       # Kịch bản DDL 11 bảng chuẩn + View + Trigger
├── insert_sample_data.sql       # Kịch bản DML nạp dữ liệu mẫu
├── setup_security_roles.sql     # Cấu hình Server Logins, DB Roles & Phân quyền
└── README.md                    # Tài liệu hướng dẫn & Báo cáo đồ án
```

---

## 5. HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN

### Bước 1: Khởi Tạo Cơ Sở Dữ Liệu trên SQL Server

1. Mở SQL Server Management Studio (SSMS) và kết nối tới máy chủ SQL Server của bạn (ví dụ: `localhost\SQLEXPRESS`).
2. Mở và chạy lần lượt 3 file script SQL theo đúng thứ tự:
   - **File 1:** `QLTV_11_tables (1).sql` -> Tạo database QLTV, 11 bảng chuẩn, Filtered Indexes, View `v_ChiTietPhieuMuon_Phat` và Trigger `trg_DongBoTrangThaiSach`.
   - **File 2:** `insert_sample_data.sql` -> Nạp dữ liệu danh mục, sách, độc giả và nhân viên mẫu.
   - **File 3:** `setup_security_roles.sql` -> Tạo Server Logins (`admin`, `nv_mai`, `nv_nam`), tạo Database Users, gán Database Roles (`QUANLY`, `THUTHU`) và Stored Procedure `sp_LayThongTinHienTai`.

---

### Bước 2: Cài Đặt Môi Trường Python

1. Máy tính cài đặt Python 3.10 trở lên.
2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install customtkinter pyodbc
   ```
3. Đảm bảo máy đã cài sẵn Microsoft ODBC Driver for SQL Server (Driver 18 hoặc 17).

---

### Bước 3: Cấu Hình Kết Nối (db.py)

Mở file `db.py` và kiểm tra tên máy chủ:
```python
SERVER_NAME = r"localhost\SQLEXPRESS"  # Thay đổi nếu SQL Server của bạn có tên khác
DATABASE_NAME = "QLTV"
```

---

### Bước 4: Khởi Chạy Ứng Dụng

Chạy file `login.py`:
```bash
python login.py
```

---

## 6. DANH SÁCH TÀI KHOẢN ĐĂNG NHẬP THỬ NGHIỆM

| Tên Đăng Nhập | Mật Khẩu | Vai Trò (Database Role) | Quyền Hạn Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| **admin** | `123456` | **QUANLY** (Ban Quản Lý) | Toàn quyền: Nhập đầu sách mới, thêm sách vào kho, thanh lý sách, mượn trả, quản lý độc giả, xem báo cáo |
| **nv_mai** | `123456` | **THUTHU** (Tổ Phục Vụ) | Nghiệp vụ phục vụ bạn đọc: Cấp thẻ độc giả, gia hạn thẻ, lập phiếu mượn/trả, báo sách hỏng, xem thống kê |
| **nv_nam** | `123456` | **THUTHU** (Tổ Phục Vụ) | Nghiệp vụ phục vụ bạn đọc: Cấp thẻ độc giả, gia hạn thẻ, lập phiếu mượn/trả, báo sách hỏng, xem thống kê |
