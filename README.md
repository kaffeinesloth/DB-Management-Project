# HỆ THỐNG QUẢN LÝ THƯ VIỆN (QLTV)
> Đồ án môn học: Hệ Quản Trị Cơ Sở Dữ Liệu  
> Kiến trúc: 2-Tier Layered Architecture (Python CustomTkinter Desktop GUI + SQL Server Authentication)

---

## 1. GIỚI THIỆU ĐỒ ÁN

QLTV là phần mềm quản lý thư viện máy tính để bàn (Desktop Application) được xây dựng trên ngôn ngữ Python kết hợp giao diện hiện đại CustomTkinter (Dark Mode) và hệ quản trị cơ sở dữ liệu Microsoft SQL Server.

Phần mềm thực thi xác thực phân quyền trực tiếp qua SQL Server Authentication (Server Logins & Database Roles), tuân thủ nghiêm ngặt các quy tắc nghiệp vụ quản lý mượn/trả sách, kiểm soát hạn thẻ độc giả, giới hạn số sách mượn và tự động tính tiền phạt trễ hạn/hư hỏng/mất sách.

---

## 2. CÔNG NGHỆ SỬ DỤNG

* Ngôn ngữ: Python 3.10+
* Giao diện (GUI): CustomTkinter, Tkinter (Dark Theme #1E2229, #242830)
* Hệ quản trị CSDL: Microsoft SQL Server (SQL Express / Local Instance)
* Kết nối CSDL: pyodbc (Hỗ trợ ODBC Driver 18 & 17 for SQL Server)
* Bảo mật & Phân quyền: SQL Server Logins, DB Users, DB Roles (QUANLY, THUTHU), Stored Procedures.

---

## 3. CHỨC NĂNG CHÍNH & QUY TẮC NGHIỆP VỤ

### 3.1. Đăng Nhập & Phân Quyền (login.py & db.py)
* Xác thực tài khoản trực tiếp bằng SQL Server Login (UID / PWD).
* Tự động nhận diện Mã nhân viên (MANV), Họ tên và Nhóm quyền (QUANLY / THUTHU).
* Cơ chế tự động khôi phục placeholder text và bảo mật phiên đăng nhập (CURRENT_SESSION).

### 3.2. Quản Lý Độc Giả (ui/tabs/tab_docgia.py)
* CRUD Độc giả: Thêm mới, cập nhật, tìm kiếm đa tiêu chí (Tên, CMND/CCCD, SĐT, Email).
* Validation: Tự động kiểm tra chống trùng lặp Số CMND/CCCD và Email trong CSDL.
* Thời hạn thẻ: Tự động tính ngày làm thẻ và ngày hết hạn (+4 năm).
* Nghiệp vụ thẻ: Gia hạn thẻ (+12 tháng), Khóa / Mở khóa thẻ độc giả (HOATDONG = 0/1).

### 3.3. Quản Lý Sách & Kho (ui/tabs/tab_sach.py)
* Đầu Sách (ISBN): Tạo đầu sách mới với đầy đủ 12 thuộc tính (ISBN, Tên sách, Giá bìa, Thể loại, Tác giả, Ngôn ngữ, NXB, Khổ sách, Số trang, Lần XB, Nội dung tóm tắt).
* Cuốn Sách Vật Lý (SACH): Nhập bản sao vật lý vào kho gắn với Vị trí Ngăn tủ / Kệ.
* Kiểm kê kho: Đánh dấu sách hư hỏng (TINHTRANG = 0) hoặc Khôi phục sách tốt (TINHTRANG = 1).

### 3.4. Quản Lý Mượn / Trả Sách & Xử Phạt (ui/tabs/tab_muontra.py)
* Ràng buộc Mượn sách:
  - Thẻ độc giả phải còn hạn (NGAYHETHAN >= GETDATE()) và đang hoạt động (HOATDONG = 1).
  - Độc giả không được giữ quá 3 cuốn sách chưa trả (SUM CT_PHIEUMUON.TRA = 0 <= 3).
  - Cuốn sách mượn phải sẵn sàng (CHOMUON = 0, TINHTRANG = 1).
  - Lập phiếu mượn thực hiện an toàn trong 1 SQL Transaction.
* Ràng buộc Trả sách & Tính Phạt tự động:
  - Trễ hạn: Mượn mang về quá 30 ngày -> Phạt trễ = (Số ngày trễ) * 500 VNĐ.
  - Hư hỏng sách: Phạt 50% giá bìa (ISBN.GIA).
  - Mất sách: Bồi thường 100% giá bìa (ISBN.GIA).

### 3.5. Báo Cáo Thống Kê (ui/tabs/tab_thongke.py)
* KPI Dashboard: Tổng số Đầu sách, Tổng cuốn sách, Sách đang cho mượn, Độc giả hoạt động, Số lượt quá hạn và Tiền phạt ước tính.
* Báo cáo chuyên sâu:
  - Danh sách Độc giả đang giữ sách quá hạn kèm số tiền phạt dự tính.
  - Thống kê Tần suất mượn sách (Xếp hạng các đầu sách mượn nhiều nhất / ít nhất).

---

## 4. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
QLTV/
├── dao/                         # Data Access Objects (Xử lý truy vấn CSDL)
│   ├── __init__.py
│   ├── docgia_dao.py            # DAO Quản lý độc giả & thẻ
│   ├── sach_dao.py              # DAO Quản lý ISBN, Sách vật lý, Ngăn tủ
│   ├── muontra_dao.py           # DAO Quản lý Mượn/Trả sách & Tính phạt
│   └── thongke_dao.py           # DAO Thống kê KPI & Báo cáo
├── ui/                          # User Interface (Tầng giao diện CustomTkinter)
│   ├── __init__.py
│   ├── ctk_patch.py             # Patch sửa lỗi placeholder cho CTkEntry
│   ├── main_dashboard.py        # Màn hình chính & Sidebar điều hướng
│   └── tabs/
│       ├── __init__.py
│       ├── tab_docgia.py        # Giao diện Quản lý Độc giả
│       ├── tab_sach.py          # Giao diện Quản lý Sách & Kho
│       ├── tab_muontra.py       # Giao diện Mượn/Trả sách & Hóa đơn phạt
│       └── tab_thongke.py       # Giao diện Báo cáo Thống kê
├── db.py                        # Quản lý kết nối pyodbc & Session người dùng
├── login.py                     # Màn hình Đăng nhập (SQL Authentication)
├── QLTV_11_tables (1).sql       # Kịch bản DDL khởi tạo CSDL 11 bảng
├── insert_sample_data.sql       # Kịch bản DML nạp dữ liệu thử nghiệm
├── setup_security_roles.sql     # Cấu hình Server Logins, DB Roles & SPs
└── README.md                    # Hướng dẫn cài đặt & vận hành hệ thống
```

---

## 5. HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN

### Bước 1: Khởi Tạo Cơ Sở Dữ Liệu trên SQL Server

1. Mở SQL Server Management Studio (SSMS) và kết nối tới máy chủ SQL Server của bạn (ví dụ: localhost\SQLEXPRESS).
2. Mở và chạy lần lượt 3 file SQL theo đúng thứ tự sau:
   - File 1: QLTV_11_tables (1).sql -> Tạo database QLTV cùng 11 bảng CSDL, khóa chính, khóa ngoại, ràng buộc CHECK và UNIQUE.
   - File 2: insert_sample_data.sql -> Nạp dữ liệu mẫu cho các bảng danh mục, đầu sách, cuốn sách, độc giả và nhân viên.
   - File 3: setup_security_roles.sql -> Khởi tạo Server Logins (admin, nv_mai, nv_nam), gán Database Roles (QUANLY, THUTHU) và tạo các Stored Procedures tra cứu.

---

### Bước 2: Cài Đặt Môi Trường Python

1. Đảm bảo máy tính đã cài đặt Python 3.10 trở lên.
2. Cài đặt các thư viện bắt buộc qua terminal / cmd:
   ```bash
   pip install customtkinter pyodbc
   ```
3. Đảm bảo máy tính đã có ODBC Driver for SQL Server (Driver 18 hoặc Driver 17).

---

### Bước 3: Cấu Hình Kết Nối CSDL (db.py)

Mở file db.py và kiểm tra hằng số SERVER_NAME:
```python
SERVER_NAME = r"localhost\SQLEXPRESS"  # Thay đổi nếu SQL Server của bạn tên khác
DATABASE_NAME = "QLTV"
```

---

### Bước 4: Khởi Chạy Ứng Dụng

Chạy file login.py để mở màn hình đăng nhập:
```bash
python login.py
```

---

## 6. ĐĂNG NHẬP THỬ NGHIỆM

Bạn có thể sử dụng các tài khoản SQL Server Logins đã được tạo sẵn từ file setup_security_roles.sql:

| Tên Đăng Nhập | Mật Khẩu | Vai Trò (Database Role) | Quyền Hạn |
| :--- | :--- | :--- | :--- |
| admin | Admin@123 | QUANLY | Toàn quyền quản trị hệ thống |
| nv_mai | 123456 | THUTHU | Quản lý độc giả, sách, mượn trả & thống kê |
| nv_nam | 123456 | THUTHU | Quản lý độc giả, sách, mượn trả & thống kê |

---

## 7. GIẤY PHÉP & TÁC GIẢ

* Đồ án: Quản Lý Thư Viện (QLTV) - Hệ Quản Trị Cơ Sở Dữ Liệu
* Phát triển bởi: Nhóm Sinh Viên Thực Hiện Đồ Án
