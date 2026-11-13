"""Validation and SQL Server operations for readers and library cards."""

from calendar import monthrange
from datetime import datetime
import re
from typing import Any, Dict, List, Optional

from database import (
    FK_DELETE_MESSAGE, PERMISSION_DENIED, PRIMARY_KEY, TRUNCATION, UNIQUE_INDEX,
    get_connection, has_error_code, is_fk_violation,
)


class ReaderActions:
    """Business rules and parameterized queries for ``dbo.DOCGIA``."""

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
    def delete(madg: int) -> bool:
        """Delete a reader card. A card with loan history is protected by FK (error 547)."""
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM dbo.DOCGIA WHERE MADG = ?;", (int(madg),))
                deleted = cursor.rowcount == 1
                if not deleted:
                    raise ValueError(f"Không tìm thấy thẻ độc giả mã {madg}; vui lòng làm mới danh sách!")
                conn.commit()
                return True
            except ValueError:
                conn.rollback()
                raise
            except Exception as error:
                conn.rollback()
                ReaderActions._raise_database_error(error)
        return False

    @staticmethod
    def get_all(limit: int = 500) -> List[Dict[str, Any]]:
        """Return the newest reader cards, including inactive card history."""
        safe_limit = max(1, min(int(limit), 1000))
        query = f"""
            SELECT TOP ({safe_limit})
                MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                CONVERT(VARCHAR(10), NGAYSINH, 103) AS NgaySinh,
                DIACHI, DIENTHOAI,
                CONVERT(VARCHAR(10), NGAYLAMTHE, 103) AS NgayLamThe,
                CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHan,
                HOATDONG
            FROM dbo.DOCGIA
            ORDER BY MADG DESC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(madg: int) -> Optional[Dict[str, Any]]:
        """Return one reader card with raw date values."""
        query = """
            SELECT MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                   NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
            FROM dbo.DOCGIA
            WHERE MADG = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (int(madg),))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))

    @staticmethod
    def search(keyword: str) -> List[Dict[str, Any]]:
        """Search by name, identity number, phone, email, or card number."""
        clean_keyword = keyword.strip()
        if not clean_keyword:
            return ReaderActions.get_all()
        pattern = f"%{clean_keyword}%"
        query = """
            SELECT MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                   CONVERT(VARCHAR(10), NGAYSINH, 103) AS NgaySinh,
                   DIACHI, DIENTHOAI,
                   CONVERT(VARCHAR(10), NGAYLAMTHE, 103) AS NgayLamThe,
                   CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHan,
                   HOATDONG
            FROM dbo.DOCGIA
            WHERE TENDG LIKE ? OR HODG LIKE ? OR SOCMND LIKE ?
               OR DIENTHOAI LIKE ? OR EMAILDG LIKE ?
               OR CAST(MADG AS VARCHAR(20)) LIKE ?
            ORDER BY MADG DESC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern,) * 6)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def check_cmnd_exists(socmnd: str, exclude_id: Optional[int] = None) -> bool:
        """Check whether an identity number already has an active card."""
        query = "SELECT COUNT(*) FROM dbo.DOCGIA WHERE SOCMND = ? AND HOATDONG = 1"
        params: List[Any] = [socmnd.strip()]
        if exclude_id is not None:
            query += " AND MADG <> ?"
            params.append(int(exclude_id))
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0] > 0

    @staticmethod
    def check_email_exists(email: str, exclude_id: Optional[int] = None) -> bool:
        """Check whether an email is already attached to another active card."""
        clean_email = email.strip()
        if not clean_email:
            return False
        query = "SELECT COUNT(*) FROM dbo.DOCGIA WHERE EMAILDG = ? AND HOATDONG = 1"
        params: List[Any] = [clean_email]
        if exclude_id is not None:
            query += " AND MADG <> ?"
            params.append(int(exclude_id))
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0] > 0

    @staticmethod
    def insert(data: Dict[str, Any]) -> int:
        """Insert a reader card and return its generated ``MADG``."""
        normalized = ReaderActions.validate_reader_data(data)
        query = """
            INSERT INTO dbo.DOCGIA (
                HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
            )
            OUTPUT INSERTED.MADG
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (
                    normalized["HODG"], normalized["TENDG"], normalized["EMAILDG"],
                    normalized["SOCMND"], normalized["GIOITINH"], normalized.get("NGAYSINH"),
                    normalized["DIACHI"], normalized["DIENTHOAI"], normalized["NGAYLAMTHE"],
                    normalized["NGAYHETHAN"], normalized["HOATDONG"],
                ))
                new_id = int(cursor.fetchone()[0])
                conn.commit()
                return new_id
            except Exception as error:
                conn.rollback()
                ReaderActions._raise_database_error(error)
        raise RuntimeError("Không thể cấp thẻ độc giả!")

    @staticmethod
    def update(madg: int, data: Dict[str, Any]) -> bool:
        """Update editable details while preserving the card's identity and history fields."""
        select_current = """
            SELECT MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                   NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
            FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
            WHERE MADG = ?;
        """
        check_identity = """
            SELECT COUNT(*)
            FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
            WHERE SOCMND = ? AND SOCMND <> ?;
        """
        check_email = """
            SELECT COUNT(*)
            FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
            WHERE EMAILDG = ? AND HOATDONG = 1 AND MADG <> ?;
        """
        update_identity_history = """
            UPDATE dbo.DOCGIA SET SOCMND = ? WHERE SOCMND = ?;
        """
        update_reader = """
            UPDATE dbo.DOCGIA
            SET HODG = ?, TENDG = ?, EMAILDG = ?, SOCMND = ?, GIOITINH = ?,
                NGAYSINH = ?, DIACHI = ?, DIENTHOAI = ?
            WHERE MADG = ? AND HOATDONG = 1;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(select_current, (int(madg),))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Không tìm thấy thẻ độc giả mã {madg}!")
                if not row[11]:
                    raise ValueError(
                        "Không thể sửa thẻ đã khóa vì đây là dữ liệu lịch sử. "
                        "Hãy chọn thẻ đang hoạt động của độc giả."
                    )

                editable_fields = (
                    "HODG", "TENDG", "EMAILDG", "SOCMND", "GIOITINH",
                    "NGAYSINH", "DIACHI", "DIENTHOAI",
                )
                current = {
                    "HODG": row[1], "TENDG": row[2], "EMAILDG": row[3],
                    "SOCMND": row[4], "GIOITINH": row[5], "NGAYSINH": row[6],
                    "DIACHI": row[7], "DIENTHOAI": row[8], "NGAYLAMTHE": row[9],
                    "NGAYHETHAN": row[10], "HOATDONG": row[11],
                }
                for field in editable_fields:
                    if field in data:
                        current[field] = data[field]
                normalized = ReaderActions.validate_reader_data(current)

                old_identity = str(row[4])
                new_identity = normalized["SOCMND"]
                if new_identity != old_identity:
                    cursor.execute(check_identity, (new_identity, old_identity))
                    if cursor.fetchone()[0] > 0:
                        raise ValueError("CMND/CCCD mới đã thuộc về một độc giả khác!")

                if normalized["EMAILDG"]:
                    cursor.execute(check_email, (normalized["EMAILDG"], int(madg)))
                    if cursor.fetchone()[0] > 0:
                        raise ValueError("Email này đã được đăng ký cho một thẻ đang hoạt động khác!")

                # SOCMND links replacement-card history for person-level loan limits.
                # A correction must therefore be applied to every historical card.
                if new_identity != old_identity:
                    cursor.execute(update_identity_history, (new_identity, old_identity))

                cursor.execute(update_reader, (
                    normalized["HODG"], normalized["TENDG"], normalized["EMAILDG"],
                    normalized["SOCMND"], normalized["GIOITINH"], normalized.get("NGAYSINH"),
                    normalized["DIACHI"], normalized["DIENTHOAI"], int(madg),
                ))
                changed = cursor.rowcount == 1
                if not changed:
                    raise ValueError("Thẻ không còn hoạt động; vui lòng làm mới danh sách!")
                conn.commit()
                return True
            except ValueError:
                conn.rollback()
                raise
            except Exception as error:
                conn.rollback()
                ReaderActions._raise_database_error(error)
        return False

    @staticmethod
    def gia_han_the(madg: int, so_thang: int = 12) -> bool:
        """Extend a card without reactivating a deliberately locked old card."""
        months = int(so_thang)
        if months <= 0 or months > 60:
            raise ValueError("Số tháng gia hạn phải từ 1 đến 60!")
        query = """
            UPDATE dbo.DOCGIA
            SET NGAYHETHAN = DATEADD(MONTH, ?,
                CASE WHEN NGAYHETHAN < GETDATE() THEN GETDATE() ELSE NGAYHETHAN END)
            WHERE MADG = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (months, int(madg)))
                changed = cursor.rowcount > 0
                conn.commit()
                return changed
            except Exception as error:
                conn.rollback()
                ReaderActions._raise_database_error(error)
        return False

    @staticmethod
    def toggle_trang_thai(madg: int, hoat_dong: bool) -> bool:
        """Activate or lock a card; SQL Server prevents two active cards per identity."""
        query = "UPDATE dbo.DOCGIA SET HOATDONG = ? WHERE MADG = ?;"
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (1 if hoat_dong else 0, int(madg)))
                changed = cursor.rowcount > 0
                conn.commit()
                return changed
            except Exception as error:
                conn.rollback()
                ReaderActions._raise_database_error(error)
        return False

    @staticmethod
    def cap_lai_the_mat(old_madg: int, new_data: Optional[Dict[str, Any]] = None, so_thang: int = 12) -> int:
        """Atomically lock a lost card and issue a new ``MADG`` for the same person."""
        months = int(so_thang)
        if months <= 0 or months > 60:
            raise ValueError("Thời hạn thẻ cấp lại phải từ 1 đến 60 tháng!")
        select_old = """
            SELECT HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                   NGAYSINH, DIACHI, DIENTHOAI, HOATDONG
            FROM dbo.DOCGIA WITH (UPDLOCK, HOLDLOCK)
            WHERE MADG = ?;
        """
        deactivate_old = "UPDATE dbo.DOCGIA SET HOATDONG = 0 WHERE MADG = ? AND HOATDONG = 1;"
        insert_new = """
            INSERT INTO dbo.DOCGIA (
                HODG, TENDG, EMAILDG, SOCMND, GIOITINH,
                NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
            )
            OUTPUT INSERTED.MADG
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(select_old, (int(old_madg),))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Không tìm thấy thẻ độc giả mã {old_madg}!")
                if not row[8]:
                    raise ValueError("Thẻ được chọn đã bị khóa nên không thể cấp lại lần nữa!")

                issue_date = datetime.now()
                replacement = {
                    "HODG": row[0], "TENDG": row[1], "EMAILDG": row[2], "SOCMND": row[3],
                    "GIOITINH": row[4], "NGAYSINH": row[5], "DIACHI": row[6], "DIENTHOAI": row[7],
                    "NGAYLAMTHE": issue_date,
                    "NGAYHETHAN": ReaderActions.add_months(issue_date, months),
                    "HOATDONG": 1,
                }
                if new_data:
                    for field in ("HODG", "TENDG", "EMAILDG", "SOCMND", "GIOITINH", "NGAYSINH", "DIACHI", "DIENTHOAI"):
                        if field in new_data:
                            replacement[field] = new_data[field]
                replacement = ReaderActions.validate_reader_data(replacement)

                cursor.execute(deactivate_old, (int(old_madg),))
                if cursor.rowcount != 1:
                    raise ValueError("Thẻ cũ không còn hoạt động; vui lòng làm mới danh sách!")
                cursor.execute(insert_new, (
                    replacement["HODG"], replacement["TENDG"], replacement["EMAILDG"],
                    replacement["SOCMND"], replacement["GIOITINH"], replacement.get("NGAYSINH"),
                    replacement["DIACHI"], replacement["DIENTHOAI"], replacement["NGAYLAMTHE"],
                    replacement["NGAYHETHAN"],
                ))
                new_id = int(cursor.fetchone()[0])
                conn.commit()
                return new_id
            except ValueError:
                conn.rollback()
                raise
            except Exception as error:
                conn.rollback()
                ReaderActions._raise_database_error(error)
        raise RuntimeError("Không thể cấp lại thẻ độc giả!")

    @staticmethod
    def kiem_tra_the_hop_le_muon_sach(madg: int) -> tuple[bool, str, int]:
        """Validate a card and count active loans across all cards of the same person."""
        query_card = """
            SELECT HOATDONG,
                   CASE WHEN NGAYHETHAN < GETDATE() THEN 1 ELSE 0 END AS DaHetHan,
                   CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHanStr,
                   SOCMND
            FROM dbo.DOCGIA
            WHERE MADG = ?;
        """
        query_borrowed_count = """
            SELECT COUNT(*)
            FROM dbo.CT_PHIEUMUON AS ct
            INNER JOIN dbo.PHIEUMUON AS pm ON ct.MAPHIEU = pm.MAPHIEU
            INNER JOIN dbo.DOCGIA AS dg ON pm.MADG = dg.MADG
            WHERE dg.SOCMND = ? AND ct.TRA = 0;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_card, (int(madg),))
            row = cursor.fetchone()
            if not row:
                return False, f"Không tìm thấy thẻ độc giả mã {madg}!", 0

            active, expired, expiry_text, identity_number = row
            if not active:
                return False, "Thẻ độc giả đang bị KHÓA! Không thể mượn sách.", 0
            if expired:
                return False, f"Thẻ độc giả đã HẾT HẠN từ ngày {expiry_text}! Vui lòng gia hạn thẻ.", 0

            cursor.execute(query_borrowed_count, (identity_number,))
            active_books = int(cursor.fetchone()[0])
            if active_books >= ReaderActions.MAX_ACTIVE_BOOKS:
                return False, (
                    f"Độc giả đang giữ {active_books} cuốn chưa trả trên các thẻ đã cấp; "
                    "đã đạt tối đa 3 cuốn!"
                ), active_books
            return True, "Thẻ hợp lệ", active_books


DocGiaDAO = ReaderActions
