"""Validation and SQL Server operations for readers and library cards.

Every database operation calls a stored procedure in sql/08_server_side_crud.sql
(server-side processing). Python only validates input for friendly UI messages
and sends EXEC; filtering, locking, uniqueness and state rules run on SQL Server.
"""

from calendar import monthrange
from datetime import datetime
import re
from typing import Any, Dict, List, Optional

from database import (
    FK_DELETE_MESSAGE, PERMISSION_DENIED, PRIMARY_KEY, TRUNCATION, UNIQUE_INDEX,
    call_one, call_rows, call_write, has_error_code, is_business_error,
    is_fk_violation, server_message,
)


class ReaderActions:
    """Business rules and stored-procedure calls for ``dbo.DOCGIA``."""

    MAX_ACTIVE_BOOKS = 3
    EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    @staticmethod
    def add_months(value: datetime, months: int) -> datetime:
        """Return ``value`` shifted by a whole number of calendar months."""
        months = int(months)
        if months <= 0:
            raise ValueError("Thời hạn thẻ phải lớn hơn 0 tháng!")
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    @staticmethod
    def validate_reader_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize values before they reach SQL Server."""
        normalized = dict(data)
        ho = str(normalized.get("HODG") or "").strip()
        ten = str(normalized.get("TENDG") or "").strip()
        socmnd = str(normalized.get("SOCMND") or "").strip()
        email = str(normalized.get("EMAILDG") or "").strip()
        phone = str(normalized.get("DIENTHOAI") or "").strip()
        address = str(normalized.get("DIACHI") or "").strip()

        if not ho or not ten:
            raise ValueError("Vui lòng nhập đầy đủ họ đệm và tên độc giả!")
        if len(ho) > 50:
            raise ValueError("Họ đệm không được vượt quá 50 ký tự!")
        if len(ten) > 12:
            raise ValueError("Tên độc giả không được vượt quá 12 ký tự!")
        if not socmnd.isdigit() or len(socmnd) not in (9, 12):
            raise ValueError("CMND/CCCD phải gồm 9 hoặc 12 chữ số!")
        if email and (len(email) > 50 or not ReaderActions.EMAIL_PATTERN.fullmatch(email)):
            raise ValueError("Email không hợp lệ hoặc vượt quá 50 ký tự!")
        if phone and (not phone.isdigit() or len(phone) not in (10, 11)):
            raise ValueError("Số điện thoại phải gồm 10 hoặc 11 chữ số!")
        if len(address) > 100:
            raise ValueError("Địa chỉ không được vượt quá 100 ký tự!")

        birth_date = normalized.get("NGAYSINH")
        if birth_date is not None:
            if not isinstance(birth_date, datetime):
                raise ValueError("Ngày sinh không hợp lệ!")
            if birth_date.year < 1900:
                raise ValueError("Ngày sinh phải từ năm 1900 trở đi!")
            if birth_date.date() > datetime.now().date():
                raise ValueError("Ngày sinh không được nằm trong tương lai!")

        issue_date = normalized.get("NGAYLAMTHE") or datetime.now()
        if not isinstance(issue_date, datetime):
            raise ValueError("Ngày làm thẻ không hợp lệ!")
        expiry_date = normalized.get("NGAYHETHAN") or ReaderActions.add_months(issue_date, 12)
        if not isinstance(expiry_date, datetime):
            raise ValueError("Ngày làm thẻ hoặc ngày hết hạn không hợp lệ!")
        if expiry_date < issue_date:
            raise ValueError("Ngày hết hạn không được trước ngày làm thẻ!")

        gender = normalized.get("GIOITINH", 1)
        if gender not in (0, 1, False, True):
            raise ValueError("Giới tính không hợp lệ!")

        normalized.update(
            {
                "HODG": ho,
                "TENDG": ten,
                "SOCMND": socmnd,
                "EMAILDG": email or None,
                "DIENTHOAI": phone or None,
                "DIACHI": address or None,
                "GIOITINH": int(gender),
                "NGAYLAMTHE": issue_date,
                "NGAYHETHAN": expiry_date,
                "HOATDONG": 1 if normalized.get("HOATDONG", 1) else 0,
            }
        )
        return normalized


    @staticmethod
    def _raise_database_error(error: Exception) -> None:
        """Translate SQL Server failures by NATIVE ERROR CODE into UI messages."""
        if is_business_error(error):                                 # THROW 5xxxx from the SP
            raise ValueError(server_message(error)) from error
        if is_fk_violation(error):                                   # 547
            raise ValueError(FK_DELETE_MESSAGE) from error
        if "UX_DOCGIA_SOCMND_ACTIVE" in str(error) or has_error_code(error, UNIQUE_INDEX, PRIMARY_KEY):
            raise ValueError("CMND/CCCD này đã có một thẻ đang hoạt động!") from error
        if has_error_code(error, *TRUNCATION):
            raise ValueError("Một trường dữ liệu vượt quá độ dài cho phép của cơ sở dữ liệu!") from error
        if has_error_code(error, PERMISSION_DENIED):
            raise PermissionError("Tài khoản hiện tại không có quyền thực hiện thao tác này!") from error
        raise RuntimeError(f"Lỗi SQL Server khi xử lý độc giả: {error}") from error

    @staticmethod
    def _write(sql: str, params: tuple) -> Optional[Dict[str, Any]]:
        """Run a writing procedure; map its errors to UI exceptions."""
        try:
            return call_write(sql, params)
        except (ValueError, PermissionError):
            raise
        except Exception as error:
            ReaderActions._raise_database_error(error)
        return None

    # ----------------------------------------------------------------- reads
    @staticmethod
    def get_all(limit: int = 500) -> List[Dict[str, Any]]:
        """Return the newest reader cards, including inactive card history."""
        safe_limit = max(1, min(int(limit), 1000))
        return call_rows("EXEC dbo.sp_DocGia_DanhSach @Keyword=?, @Top=?", (None, safe_limit))

    @staticmethod
    def search(keyword: str) -> List[Dict[str, Any]]:
        """Search by name, identity number, phone, email, or card number (on SQL Server)."""
        clean_keyword = (keyword or "").strip()
        if not clean_keyword:
            return ReaderActions.get_all()
        return call_rows("EXEC dbo.sp_DocGia_DanhSach @Keyword=?", (clean_keyword,))

    @staticmethod
    def get_active_readers() -> List[Dict[str, Any]]:
        """Active cards only, filtered and sorted by SQL Server (borrowing picker)."""
        return call_rows("EXEC dbo.sp_DocGia_DanhSachHoatDong")

    @staticmethod
    def get_by_id(madg: int) -> Optional[Dict[str, Any]]:
        """Return one reader card with raw date values."""
        return call_one("EXEC dbo.sp_DocGia_ChiTiet @MADG=?", (int(madg),))

    @staticmethod
    def _duplicates(socmnd: Optional[str], email: Optional[str],
                    exclude_id: Optional[int]) -> Dict[str, Any]:
        return call_one(
            "EXEC dbo.sp_DocGia_KiemTraTrung @SOCMND=?, @EMAILDG=?, @ExcludeMADG=?",
            (socmnd, email, None if exclude_id is None else int(exclude_id)),
        ) or {}

    @staticmethod
    def check_cmnd_exists(socmnd: str, exclude_id: Optional[int] = None) -> bool:
        """Check whether an identity number already has an active card."""
        return bool(ReaderActions._duplicates(socmnd.strip(), None, exclude_id).get("CmndTrung"))

    @staticmethod
    def check_email_exists(email: str, exclude_id: Optional[int] = None) -> bool:
        """Check whether an email is already attached to another active card."""
        clean_email = email.strip()
        if not clean_email:
            return False
        return bool(ReaderActions._duplicates(None, clean_email, exclude_id).get("EmailTrung"))

    # ---------------------------------------------------------------- writes
    @staticmethod
    def insert(data: Dict[str, Any]) -> int:
        """Insert a reader card and return its generated ``MADG``."""
        n = ReaderActions.validate_reader_data(data)
        row = ReaderActions._write(
            "EXEC dbo.sp_DocGia_Them @HODG=?, @TENDG=?, @EMAILDG=?, @SOCMND=?, @GIOITINH=?, "
            "@NGAYSINH=?, @DIACHI=?, @DIENTHOAI=?, @NGAYLAMTHE=?, @NGAYHETHAN=?, @HOATDONG=?",
            (n["HODG"], n["TENDG"], n["EMAILDG"], n["SOCMND"], n["GIOITINH"], n.get("NGAYSINH"),
             n["DIACHI"], n["DIENTHOAI"], n["NGAYLAMTHE"], n["NGAYHETHAN"], n["HOATDONG"]),
        )
        if not row or row.get("MADG") is None:
            raise RuntimeError("Không thể cấp thẻ độc giả!")
        return int(row["MADG"])

    @staticmethod
    def update(madg: int, data: Dict[str, Any]) -> bool:
        """Update editable details; locking, uniqueness and history rules run in the SP."""
        current = ReaderActions.get_by_id(madg)
        if not current:
            raise ValueError(f"Không tìm thấy thẻ độc giả mã {madg}!")
        if not current["HOATDONG"]:
            raise ValueError(
                "Không thể sửa thẻ đã khóa vì đây là dữ liệu lịch sử. "
                "Hãy chọn thẻ đang hoạt động của độc giả."
            )
        merged = dict(current)
        for field in ("HODG", "TENDG", "EMAILDG", "SOCMND", "GIOITINH",
                      "NGAYSINH", "DIACHI", "DIENTHOAI"):
            if field in data:
                merged[field] = data[field]
        n = ReaderActions.validate_reader_data(merged)
        ReaderActions._write(
            "EXEC dbo.sp_DocGia_CapNhat @MADG=?, @HODG=?, @TENDG=?, @EMAILDG=?, @SOCMND=?, "
            "@GIOITINH=?, @NGAYSINH=?, @DIACHI=?, @DIENTHOAI=?",
            (int(madg), n["HODG"], n["TENDG"], n["EMAILDG"], n["SOCMND"], n["GIOITINH"],
             n.get("NGAYSINH"), n["DIACHI"], n["DIENTHOAI"]),
        )
        return True

    @staticmethod
    def delete(madg: int) -> bool:
        """Delete a reader card. A card with loan history is protected by FK (error 547)."""
        ReaderActions._write("EXEC dbo.sp_DocGia_Xoa @MADG=?", (int(madg),))
        return True

    @staticmethod
    def gia_han_the(madg: int, so_thang: int = 12) -> bool:
        """Extend a card without reactivating a deliberately locked old card."""
        months = int(so_thang)
        if months <= 0 or months > 60:
            raise ValueError("Số tháng gia hạn phải từ 1 đến 60!")
        ReaderActions._write("EXEC dbo.sp_DocGia_GiaHan @MADG=?, @SoThang=?", (int(madg), months))
        return True

    @staticmethod
    def toggle_trang_thai(madg: int, hoat_dong: bool) -> bool:
        """Activate or lock a card; SQL Server prevents two active cards per identity."""
        ReaderActions._write(
            "EXEC dbo.sp_DocGia_DoiTrangThai @MADG=?, @HoatDong=?",
            (int(madg), 1 if hoat_dong else 0),
        )
        return True

    @staticmethod
    def cap_lai_the_mat(old_madg: int, so_thang: int = 12) -> int:
        """Atomically lock a lost card and issue a new ``MADG`` for the same person."""
        months = int(so_thang)
        if months <= 0 or months > 60:
            raise ValueError("Thời hạn thẻ cấp lại phải từ 1 đến 60 tháng!")
        row = ReaderActions._write(
            "EXEC dbo.sp_DocGia_CapLaiThe @OldMADG=?, @SoThang=?", (int(old_madg), months)
        )
        if not row or row.get("MADG") is None:
            raise RuntimeError("Không thể cấp lại thẻ độc giả!")
        return int(row["MADG"])

    @staticmethod
    def kiem_tra_the_hop_le_muon_sach(madg: int) -> tuple[bool, str, int]:
        """Validate a card and count active loans across all cards of the same person."""
        row = call_one("EXEC dbo.sp_DocGia_KiemTraMuonSach @MADG=?", (int(madg),))
        if not row:
            return False, f"Không tìm thấy thẻ độc giả mã {madg}!", 0
        return bool(row["HopLe"]), str(row["LyDo"]), int(row["DangGiu"] or 0)


DocGiaDAO = ReaderActions
