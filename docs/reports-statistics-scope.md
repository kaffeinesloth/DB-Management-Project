# Reports & Statistics module — scope

Branch: `feature/reports-statistics` (from `main` @ `c166a32`). Nothing merged.

## 1. What the spec asks for

Spec: `Additional Info/De4-QLTV_Unicode_Fixed.docx`, section **Báo cáo thống kê**.

Reading-room staff produce reports **monthly or quarterly** for:

| # | Report | Source in spec |
|---|--------|----------------|
| R1 | Readers with overdue books (*Độc giả mượn sách quá hạn*) | explicit |
| R2 | Book usage frequency (*Tần suất sử dụng sách*) | explicit |

Related rules the reports must respect:
- Loan period 30 days; fine 500 VND per overdue day.
- Max 3 books per reader (already enforced by trigger).
- Readers who never return books get a notice at end of term → covered by R1 (no date cap).
- Annual stock check lists damaged books and books nobody borrows → optional R3/R4 below.

## 2. What already exists

**Database (verified live in Docker, `LibraryManagement`):**
- `v_CHITIET_MUONTRA` — every loan line with due date (`NGAYHENTRA`), overdue days and fine.
- `v_DOCGIA_MUON_QUAHAN` — unreturned + overdue lines. Live: 3 rows (reader 8 ×2, reader 9).
- `v_TANSUAT_SU_DUNG_SACH` — borrow count per title, all-time.
- Sample data: 15 titles, 30 copies, 10 loans / 12 lines, dated 2026-08-01 → 2026-10-04.
- No stored procedures or functions of ours yet.

**Python app (`main` branch):**
- `reports/report_screen.py` — placeholder ("Coming soon").
- `reports/report_actions.py` — empty.
- `database.py` — only `connection = None`; no connect helper. Every module depends on this.
- Dashboard already routes to `ReportScreen`.

## 3. Gaps

1. **No period filter.** Spec says monthly/quarterly, but `v_TANSUAT_SU_DUNG_SACH` is all-time and the overdue view is "as of now". Need a date range (from/to) on R2, and an "as of" date on R1.
2. **Overdue view uses `GETDATE()`.** Fine for "now", but a month-end report needs `@AsOf`.
3. **Late-but-returned loans not reported.** Fines collected in a period (returned late) are not in any view.
4. **No DB connection layer** in Python — shared blocker for all modules, not just reports.
5. **Sample data spans only Aug–Oct 2026**, so quarterly/monthly demos will look thin; one quarter (Q3) and a partial Q4.

## 4. Proposed work

### SQL — new file `sql/06_reports.sql` (idempotent, `CREATE OR ALTER`)
- `fn_BaoCao_QuaHan(@AsOf)` (inline TVF) — R1: reader, contact, book, borrow date, due date, days overdue, fine as of `@AsOf`.
- `fn_TanSuat_SuDung(@TuNgay, @DenNgay)` (inline TVF) — R2: per title borrow count, distinct readers, copies owned, rank; titles with 0 included.
- `sp_ThongKe_TheoKy(@Nam, @Thang = NULL, @Quy = NULL)` — summary for a month or quarter: loans, books lent, returned, returned late, fines, overdue at period end.
- Optional R3 `fn_Sach_KhongMuon(@TuNgay, @DenNgay)` — titles/copies never borrowed in the period (annual weeding list).
- Optional R4 — damaged copies (`TINHTRANG = 0`).
- `library_app_role` already has `SELECT` on schema dbo; add `GRANT EXECUTE ON SCHEMA::dbo` for the procedure.
- Wire into `docker/init-database.sh` and add checks to `sql/05_verify_database.sql` / `99_smoke_test.sql`.

### Python
- `database.py` — minimal `get_connection()` reading `.env` values (unless another module lands it first; coordinate).
- `reports/report_actions.py` — one function per report, parameterised queries, returns rows + column names.
- `reports/report_screen.py` — tabs: *Quá hạn* / *Tần suất* / *Thống kê kỳ*; period picker (month or quarter + year); `ttk.Treeview` table; summary line (totals); **Export CSV** (stdlib `csv`, no new dependency).

### Out of scope
Charts, PDF/Excel export, emailing notices, fine payment tracking (spec has no fine table).

## 5. Decisions taken (change if you disagree)
1. `database.py` got a minimal `get_connection()` (reads `.env`, falls back to `.env.example`). If a teammate owns it, merge theirs over this.
2. Stock review (damaged + not borrowed in the period) is included as one report, `fn_BaoCao_SachCanXemXet`.
3. Overdue days and fines count up to the report date: end of the period, or today if the period is still running.

## 6. Delivered
- `sql/06_reports.sql`: `fn_BaoCao_QuaHan`, `fn_BaoCao_TanSuat`, `fn_BaoCao_SachCanXemXet`, `sp_ThongKe_TheoKy`, `GRANT EXECUTE` for the app role. Run by `docker/init-database.sh` after `03`.
- `sql/05_verify_database.sql`: checks the four objects exist. `sql/99_smoke_test.sql`: fixed-date checks for every report.
- `reports/report_actions.py`, `reports/report_screen.py`: four tabs, month/quarter/year picker, CSV export.

## 7. Known unrelated issue
`05_verify_database.sql` fails on the current Docker DB because an SSMS `sysdiagrams` table (created 2026-10-22) makes 12 user tables instead of 11.

## 8. Rough size
SQL ~150 lines, Python ~250 lines. About a day including manual testing against Docker.
