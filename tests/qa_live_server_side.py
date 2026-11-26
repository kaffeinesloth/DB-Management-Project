"""Live QA for lecturer criteria 2 & 3 against a running SQL Server.

Not part of `unittest discover` (needs a database). Run against a FRESH
sample database, e.g. an isolated compose project:

    MSSQL_PORT=14339 docker compose -p qa-servercrud --env-file .env up -d
    DB_HOST=127.0.0.1,14339 py -3.10 tests/qa_live_server_side.py

Seed passwords are read from sql/03_login_and_permissions.sql at runtime and
never printed. The script changes one librarian's password (reset test), so
do not point it at a database you care about.
"""

import os
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_HOST", "127.0.0.1,14339")

import database  # noqa: E402
from account_management import account_actions as acc  # noqa: E402
from book_management.book_actions import SachDAO  # noqa: E402
from reader_management.reader_actions import DocGiaDAO  # noqa: E402

RESULTS = []


def check(name, func):
    try:
        func()
        RESULTS.append((True, name, ""))
        print(f"PASS  {name}")
    except Exception as error:  # noqa: BLE001
        RESULTS.append((False, name, f"{type(error).__name__}: {error}"))
        print(f"FAIL  {name}\n      {type(error).__name__}: {error}")
        if os.environ.get("QA_TRACE"):
            traceback.print_exc()


def expect_error(func, exc_type, fragment):
    try:
        func()
    except exc_type as error:
        assert fragment in str(error), f"message {str(error)!r} lacks {fragment!r}"
        return
    raise AssertionError(f"expected {exc_type.__name__} containing {fragment!r}")


def seed_passwords():
    text = (ROOT / "sql" / "03_login_and_permissions.sql").read_text(encoding="utf-8")
    return dict(re.findall(r"CREATE LOGIN \[(\w+)\] WITH PASSWORD = '([^']*)'", text))


def login(name, password):
    database.clear_session()
    return database.dang_nhap_he_thong(name, password)


def raw_scalar(sql):
    """QA setup only: find fixture rows (the app itself never does this)."""
    with database.get_connection() as conn:
        row = conn.cursor().execute(sql).fetchone()
        return row[0] if row else None


def main():
    pw = seed_passwords()
    roles = {}
    for name in ("admin", "nv_huong", "nv_long", "nv_nam"):
        if name in pw:
            roles[name] = login(name, pw[name])["RoleName"]
    manager = next(n for n, r in roles.items() if r == "QUANLY")
    librarians = [n for n, r in roles.items() if r == "THUTHU"]
    reset_target, librarian = librarians[0], librarians[-1]
    print(f"Manager: {manager}; librarians: {librarians}\n")

    # ================================================== QUANLY session
    login(manager, pw[manager])
    state = {}

    print("--- Criterion 2: readers (QUANLY) ---")

    def active_readers_server_filtered():
        rows = DocGiaDAO.get_active_readers()
        assert rows, "no active readers in sample data"
        ids = [int(r["MADG"]) for r in rows]
        assert ids == sorted(ids), "not ascending"
        everything = {int(r["MADG"]): r for r in DocGiaDAO.get_all(1000)}
        assert all(everything[i]["HOATDONG"] for i in ids), "locked card returned"
        locked = [i for i, r in everything.items() if not r["HOATDONG"]]
        assert not set(locked) & set(ids)
    check("sp_DocGia_DanhSachHoatDong: only active, ascending", active_readers_server_filtered)

    def search_matches_server():
        first = DocGiaDAO.get_all()[0]
        hits = DocGiaDAO.search(str(first["SOCMND"]))
        assert any(h["MADG"] == first["MADG"] for h in hits)
        assert DocGiaDAO.search("zzz_no_such_reader_zzz") == []
    check("sp_DocGia_DanhSach: search by CMND / no match", search_matches_server)

    def reader_lifecycle():
        from datetime import datetime
        new_id = DocGiaDAO.insert({
            "HODG": "QA Tự", "TENDG": "Động", "SOCMND": "990011223344",
            "EMAILDG": "qa.auto@example.com", "GIOITINH": 1,
            "NGAYSINH": datetime(2000, 2, 2), "DIENTHOAI": "0900000001",
        })
        state["reader"] = new_id
        card = DocGiaDAO.get_by_id(new_id)
        assert card and card["HOATDONG"] and card["TENDG"] == "Động"
        assert DocGiaDAO.check_cmnd_exists("990011223344")
        assert not DocGiaDAO.check_cmnd_exists("990011223344", exclude_id=new_id)
        assert DocGiaDAO.check_email_exists("qa.auto@example.com")
        DocGiaDAO.update(new_id, {"TENDG": "Sửa", "DIACHI": "QA street"})
        card = DocGiaDAO.get_by_id(new_id)
        assert card["TENDG"] == "Sửa" and card["DIACHI"] == "QA street"
        old_expiry = card["NGAYHETHAN"]
        DocGiaDAO.gia_han_the(new_id, 6)
        assert DocGiaDAO.get_by_id(new_id)["NGAYHETHAN"] > old_expiry
    check("reader add / check-duplicate / edit / extend", reader_lifecycle)

    check("duplicate active CMND is refused by SP", lambda: expect_error(
        lambda: DocGiaDAO.insert({"HODG": "QA", "TENDG": "Trùng", "SOCMND": "990011223344",
                                  "GIOITINH": 1}),
        ValueError, "CMND/CCCD"))

    def lock_then_edit_refused():
        DocGiaDAO.toggle_trang_thai(state["reader"], False)
        expect_error(lambda: DocGiaDAO.update(state["reader"], {"TENDG": "X"}),
                     ValueError, "dữ liệu lịch sử")
        valid, reason, _ = DocGiaDAO.kiem_tra_the_hop_le_muon_sach(state["reader"])
        assert not valid and "KHÓA" in reason
        DocGiaDAO.toggle_trang_thai(state["reader"], True)
    check("lock card -> edit refused, borrow check says KHÓA", lock_then_edit_refused)

    def replace_lost_card():
        new_id = DocGiaDAO.cap_lai_the_mat(state["reader"], so_thang=12)
        assert new_id != state["reader"]
        assert not DocGiaDAO.get_by_id(state["reader"])["HOATDONG"]
        assert DocGiaDAO.get_by_id(new_id)["HOATDONG"]
        expect_error(lambda: DocGiaDAO.cap_lai_the_mat(state["reader"]), ValueError, "đã bị khóa")
        state["reader2"] = new_id
    check("replace lost card is atomic; second replace refused", replace_lost_card)

    def delete_readers():
        DocGiaDAO.delete(state["reader2"])
        DocGiaDAO.delete(state["reader"])
        assert DocGiaDAO.get_by_id(state["reader"]) is None
        expect_error(lambda: DocGiaDAO.delete(state["reader"]), ValueError, "Không tìm thấy")
    check("delete readers without history; missing -> SP message", delete_readers)

    def delete_reader_with_history():
        madg = raw_scalar("SELECT TOP (1) MADG FROM dbo.PHIEUMUON")
        expect_error(lambda: DocGiaDAO.delete(madg), ValueError, "phát sinh giao dịch")
    check("delete reader with loan history -> FK 547 message", delete_reader_with_history)

    def borrow_check():
        rows = DocGiaDAO.get_active_readers()
        valid, reason, count = DocGiaDAO.kiem_tra_the_hop_le_muon_sach(rows[0]["MADG"])
        assert isinstance(valid, bool) and reason and count >= 0
        valid, reason, _ = DocGiaDAO.kiem_tra_the_hop_le_muon_sach(-5)
        assert not valid and "Không tìm thấy" in reason
    check("sp_DocGia_KiemTraMuonSach returns verdict", borrow_check)

    print("\n--- Criterion 2: books (QUANLY) ---")

    def book_reads():
        copies = SachDAO.get_all_sach()
        titles = SachDAO.get_all_isbn()
        assert copies and titles
        assert {"TheLoai", "HoTenTG", "ViTri", "GiaBia"} <= set(copies[0])
        assert {"TongBanSao", "BanSaoKhaDung"} <= set(titles[0])
        assert SachDAO.search_sach(copies[0]["MASACH"])[0]["MASACH"] == copies[0]["MASACH"]
        ready = SachDAO.get_danh_sach_sach_san_sang()
        by_id = {c["MASACH"]: c for c in copies}
        assert all(by_id[r["MASACH"]]["CHOMUON"] == 0 and by_id[r["MASACH"]]["TINHTRANG"] == 1
                   for r in ready), "unavailable copy listed as ready"
        for lookup in (SachDAO.get_danh_muc_the_loai, SachDAO.get_danh_muc_ngan_tu,
                       SachDAO.get_danh_muc_tac_gia, SachDAO.get_danh_muc_ngon_ngu):
            assert lookup()
    check("book lists, search, ready-to-lend, lookups", book_reads)

    def book_lifecycle():
        matl = SachDAO.get_danh_muc_the_loai()[0]["MATL"]
        lang = SachDAO.get_danh_muc_ngon_ngu()[0]["MANGONNGU"]
        shelf = SachDAO.get_danh_muc_ngan_tu()[0]["MANGANTU"]
        author = SachDAO.get_danh_muc_tac_gia()[0]["MATACGIA"]
        SachDAO.them_dau_sach({"ISBN": "QA00000001", "TENSACH": "QA Title", "GIA": 1000,
                               "MATL": matl, "MANGONNGU": lang}, matacgia=author)
        detail = SachDAO.get_dau_sach("QA00000001")
        assert detail["TENSACH"] == "QA Title" and detail["MATACGIA"] == author
        SachDAO.cap_nhat_dau_sach({"ISBN": "QA00000001", "TENSACH": "QA Title 2", "GIA": 2000,
                                   "MATL": matl, "MANGONNGU": lang}, matacgia=author)
        assert SachDAO.get_dau_sach("QA00000001")["TENSACH"] == "QA Title 2"
        SachDAO.them_cuon_sach("QA001", "QA00000001", shelf, 1)
        ok, _, _ = SachDAO.kiem_tra_sach_cho_muon("QA001")
        assert ok
        expect_error(lambda: SachDAO.xoa_dau_sach("QA00000001"), ValueError, "phát sinh giao dịch")
        SachDAO.cap_nhat_tinh_trang("QA001", 0)
        ok, reason, _ = SachDAO.kiem_tra_sach_cho_muon("QA001")
        assert not ok and "hư hỏng" in reason
        SachDAO.cap_nhat_cuon_sach("QA001", "QA00000001", shelf, 1)
        SachDAO.huy_cuon_sach("QA001")
        SachDAO.xoa_dau_sach("QA00000001")
        assert SachDAO.get_dau_sach("QA00000001") is None
    check("title+copy add/edit/condition/delete; title with copies -> FK", book_lifecycle)

    check("duplicate copy code -> friendly PK message", lambda: expect_error(
        lambda: SachDAO.them_cuon_sach(SachDAO.get_all_sach()[0]["MASACH"],
                                       SachDAO.get_all_sach()[0]["ISBN"],
                                       SachDAO.get_danh_muc_ngan_tu()[0]["MANGANTU"]),
        ValueError, "đã tồn tại"))

    def on_loan_copy_refused():
        masach = raw_scalar("SELECT TOP (1) MASACH FROM dbo.SACH WHERE CHOMUON = 1")
        assert masach, "sample data has no copy on loan"
        expect_error(lambda: SachDAO.huy_cuon_sach(masach), ValueError, "đang được mượn")
    check("delete copy that is on loan -> SP refuses", on_loan_copy_refused)

    check("missing copy / title -> SP not-found messages", lambda: (
        expect_error(lambda: SachDAO.huy_cuon_sach("NOPE"), ValueError, "Không tìm thấy"),
        expect_error(lambda: SachDAO.xoa_dau_sach("NOPE"), ValueError, "Không tìm thấy"),
        expect_error(lambda: SachDAO.cap_nhat_tinh_trang("NOPE", 1), ValueError, "Không tìm thấy"),
    ))

    print("\n--- Criteria 2 & 3: accounts (QUANLY) ---")

    def without_account_server_filtered():
        rows = acc.list_employees_without_account()
        everyone = acc.list_employee_accounts()
        expected = sorted(r["MANV"] for r in everyone if not r["DaCoTaiKhoan"])
        assert sorted(r["MANV"] for r in rows) == expected
        assert all(not r["DaCoTaiKhoan"] for r in rows)
    check("sp_DanhSachTaiKhoanNhanVien @ChuaCoTaiKhoan=1", without_account_server_filtered)

    # Seed passwords already equal the reset default, so the librarian first
    # changes theirs; otherwise "old password fails" would prove nothing.
    changed_pw = "QaChanged_2026"

    def librarian_changes_own_password():
        login(reset_target, pw[reset_target])
        acc.change_own_password(pw[reset_target], changed_pw, changed_pw)
        login(reset_target, changed_pw)
        login(manager, pw[manager])
    check(f"{reset_target} changes own password first", librarian_changes_own_password)

    check(f"reset password by LoginName ({reset_target})",
          lambda: acc.reset_employee_password(reset_target))
    check("reset own password refused (51043)", lambda: expect_error(
        lambda: acc.reset_employee_password(manager), Exception, "chính mình"))
    for service_login in ("library_app", "docgia", "sa"):
        check(f"reset non-employee login '{service_login}' refused (51042)", lambda s=service_login:
              expect_error(lambda: acc.reset_employee_password(s), Exception, "không thuộc nhân viên"))
    check("reset unknown login refused", lambda: expect_error(
        lambda: acc.reset_employee_password("no_such_login_qa"), Exception, "không thuộc nhân viên"))

    check(f"{reset_target} can log in with 123456 after reset",
          lambda: login(reset_target, "123456"))
    check(f"{reset_target}'s pre-reset password no longer works", lambda: expect_error(
        lambda: login(reset_target, changed_pw), ValueError, "không chính xác"))

    # ================================================== THUTHU session
    print(f"\n--- Permissions as THUTHU ({librarian}) ---")
    if librarian == reset_target:
        login(librarian, "123456")
    else:
        login(librarian, pw[librarian])

    def librarian_reader_crud():
        new_id = DocGiaDAO.insert({"HODG": "QA Thủ", "TENDG": "Thư", "SOCMND": "990099887766",
                                   "GIOITINH": 0})
        DocGiaDAO.gia_han_the(new_id, 1)
        DocGiaDAO.delete(new_id)
        assert DocGiaDAO.get_active_readers()
    check("THUTHU: reader add/extend/delete + active list", librarian_reader_crud)

    check("THUTHU: book lists readable", lambda: (
        SachDAO.get_all_sach(), SachDAO.get_all_isbn(), SachDAO.get_danh_muc_the_loai()))

    check("THUTHU: add title denied by SQL Server", lambda: expect_error(
        lambda: SachDAO.them_dau_sach({"ISBN": "QA00000009", "TENSACH": "Denied",
                                       "MATL": "TL001", "MANGONNGU": 1}),
        ValueError, "không có quyền"))
    check("THUTHU: delete copy denied by SQL Server", lambda: expect_error(
        lambda: SachDAO.huy_cuon_sach("S0001"), ValueError, "không có quyền"))
    check("THUTHU: reset password denied by SQL Server", lambda: expect_error(
        lambda: acc.reset_employee_password(manager), Exception, "permission"))

    database.clear_session()
    failed = [r for r in RESULTS if not r[0]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} QA checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
