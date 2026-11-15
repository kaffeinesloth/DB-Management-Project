"""Bản in báo cáo: dựng trang HTML khổ A4 rồi mở bằng trình duyệt để in / lưu PDF.

Bố cục theo mẫu giấy:
  - Đầu trang: tên đơn vị, tiêu đề báo cáo, kỳ báo cáo.
  - Thân: bảng có cột STT tự sinh (không lấy từ SQL).
  - Cuối trang: "TP. Hồ Chí Minh, ngày ... tháng ... năm ...", "Người lập báo cáo", họ tên.

Cột STT:
  - Báo cáo phẳng: STT chạy liên tục từ 1.
  - Báo cáo quá hạn: nhóm theo độc giả, STT nhóm chạy liên tục, STT dòng reset về 1 mỗi nhóm.
"""

from __future__ import annotations

import html
import tempfile
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Any

from reports.report_actions import ReportResult, format_value

ORGANIZATION = "THƯ VIỆN TRƯỜNG"
DEPARTMENT = "Bộ phận Phòng đọc"
CITY = "TP. Hồ Chí Minh"

# Cột không đưa lên bản in (rộng, ít giá trị khi in giấy).
HIDDEN_ON_PAPER = {"EMAILDG"}
# Cột tiền: canh phải, định dạng 1.000 đ.
MONEY_KEYS = {"TIENPHAT"}
NUMBER_KEYS = {"SOBANSAO", "SOLUOTMUON", "SODOCGIA", "SONGAYQUAHAN", "XEPHANG", "TIENPHAT"}


def vietnamese_date_line(day: date, city: str = CITY) -> str:
    """'TP. Hồ Chí Minh, ngày 16 tháng 11 năm 2026'."""
    return f"{city}, ngày {day.day:02d} tháng {day.month:02d} năm {day.year}"


def _esc(value: Any) -> str:
    return html.escape(format_value(value))


def _money(value: Any) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _cell(key: str, value: Any) -> str:
    if key == "GIATRI":  # bảng thống kê tổng hợp: giá trị hỗn hợp, canh phải đồng nhất
        if isinstance(value, (date, datetime)):
            text = f"{value:%d/%m/%Y}"
        elif isinstance(value, int) and not isinstance(value, bool):
            text = _money(value)
        else:
            text = _esc(value)
        return f'<td class="num">{text}</td>'
    if key in MONEY_KEYS:
        return f'<td class="num">{_money(value)}</td>'
    if key in NUMBER_KEYS:
        return f'<td class="num">{_esc(value)}</td>'
    if isinstance(value, (date, datetime)):
        return f'<td class="center">{value:%d/%m/%Y}</td>'  # bản in chỉ cần ngày
    return f"<td>{_esc(value)}</td>"


def _visible(result: ReportResult) -> list[int]:
    keys = result.keys or [""] * len(result.columns)
    return [i for i, key in enumerate(keys) if key not in HIDDEN_ON_PAPER]


def _flat_table(result: ReportResult) -> str:
    cols = _visible(result)
    keys = result.keys or [""] * len(result.columns)
    head = '<th class="stt">STT</th>' + "".join(
        f"<th>{html.escape(result.columns[i])}</th>" for i in cols
    )
    body = []
    for stt, row in enumerate(result.rows, start=1):
        cells = "".join(_cell(keys[i], row[i]) for i in cols)
        body.append(f'<tr><td class="stt">{stt}</td>{cells}</tr>')
    if not body:
        body.append(f'<tr><td colspan="{len(cols) + 1}" class="center empty">Không có dữ liệu</td></tr>')
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _overdue_table(result: ReportResult) -> str:
    """Nhóm theo độc giả: STT nhóm liên tục, STT dòng reset trong mỗi nhóm."""
    idx = {key: i for i, key in enumerate(result.keys)}
    reader_keys = ("MADG", "HOTENDG", "DIENTHOAI", "EMAILDG")
    line_keys = [k for k in ("MAPHIEU", "MASACH", "TENSACH", "NGAYMUON", "NGAYHENTRA",
                             "SONGAYQUAHAN", "TIENPHAT") if k in idx]
    labels = {k: result.columns[idx[k]] for k in line_keys}

    groups: dict[Any, list[tuple]] = {}
    for row in result.rows:
        groups.setdefault(row[idx["MADG"]], []).append(row)

    width = len(line_keys) + 1
    head = '<th class="stt">STT</th>' + "".join(f"<th>{html.escape(labels[k])}</th>" for k in line_keys)
    body = []
    for group_no, (_, rows) in enumerate(groups.items(), start=1):
        first = rows[0]
        name, phone = first[idx["HOTENDG"]], first[idx["DIENTHOAI"]]
        email = first[idx["EMAILDG"]] if "EMAILDG" in idx else None
        contact = " · ".join(_esc(v) for v in (phone, email) if v)
        body.append(
            f'<tr class="group"><td colspan="{width}">{group_no}. Độc giả: '
            f"<b>{_esc(name)}</b> (Mã ĐG {_esc(first[idx['MADG']])})"
            f"{' — ' + contact if contact else ''}</td></tr>"
        )
        for stt, row in enumerate(rows, start=1):
            cells = "".join(_cell(k, row[idx[k]]) for k in line_keys)
            body.append(f'<tr><td class="stt">{stt}</td>{cells}</tr>')
        subtotal = sum(int(r[idx["TIENPHAT"]] or 0) for r in rows)
        body.append(
            f'<tr class="subtotal"><td colspan="{width - 1}">Cộng: {len(rows)} cuốn</td>'
            f'<td class="num">{_money(subtotal)}</td></tr>'
        )
    if not groups:
        body.append(f'<tr><td colspan="{width}" class="center empty">Không có dữ liệu</td></tr>')
    else:
        total = sum(int(r[idx["TIENPHAT"]] or 0) for r in result.rows)
        body.append(
            f'<tr class="total"><td colspan="{width - 1}">TỔNG CỘNG: {len(groups)} độc giả, '
            f"{len(result.rows)} cuốn</td><td class=\"num\">{_money(total)}</td></tr>"
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _period_line(result: ReportResult) -> str:
    if result.period:
        start, end = result.period
        return f"Từ ngày {start:%d/%m/%Y} đến ngày {end:%d/%m/%Y}"
    return ""


def render_html(
    result: ReportResult,
    creator_name: str,
    created: date | None = None,
    creator_id: Any = None,
) -> str:
    """Trả về toàn bộ trang HTML của bản in."""
    created = created or date.today()
    grouped = result.keys[:1] == ["MADG"] and "TIENPHAT" in result.keys
    table = _overdue_table(result) if grouped else _flat_table(result)
    landscape = len(_visible(result)) > 7 and not grouped
    title = result.title.split(" - ")[0].split(" tính đến ")[0]
    subtitle = result.title[len(title):].strip(" -")
    period = _period_line(result)
    summary = f'<p class="summary">Tóm tắt: {html.escape(result.summary)}</p>' if result.summary else ""
    creator = html.escape(creator_name or "")
    creator_code = f"<div class=\"muted\">Mã NV: {html.escape(str(creator_id))}</div>" if creator_id else ""

    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<title>{html.escape(result.title)}</title>
<style>
  @page {{ size: A4 {'landscape' if landscape else 'portrait'}; margin: 15mm 15mm 18mm 20mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Times New Roman", Times, serif; font-size: 13pt; color: #000;
         background: #e5e5e5; margin: 0; }}
  .page {{ background: #fff; width: {'297mm' if landscape else '210mm'}; min-height: {'210mm' if landscape else '297mm'};
           margin: 12px auto; padding: 15mm 15mm 18mm 20mm; box-shadow: 0 0 6px rgba(0,0,0,.25); }}
  .header {{ display: flex; justify-content: space-between; font-size: 12pt; }}
  .header .left, .header .right {{ text-align: center; }}
  .header b {{ display: block; }}
  .rule {{ width: 40%; margin: 2px auto 0; border-top: 1px solid #000; }}
  h1 {{ text-align: center; font-size: 17pt; margin: 22px 0 4px; text-transform: uppercase; }}
  .sub {{ text-align: center; font-style: italic; margin: 0; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 11.5pt; }}
  th, td {{ border: 1px solid #000; padding: 4px 6px; vertical-align: top; }}
  th {{ background: #f0f0f0; text-align: center; }}
  thead {{ display: table-header-group; }}
  tr {{ page-break-inside: avoid; }}
  .stt {{ width: 9mm; text-align: center; }}
  .num {{ text-align: right; white-space: nowrap; }}
  .center {{ text-align: center; white-space: nowrap; }}
  .empty {{ font-style: italic; padding: 10px; }}
  .group td {{ background: #fafafa; }}
  .subtotal td {{ font-style: italic; text-align: right; }}
  .total td {{ font-weight: bold; text-align: right; }}
  .summary {{ margin: 10px 0 0; }}
  .sign {{ display: flex; justify-content: flex-end; margin-top: 24px; page-break-inside: avoid; }}
  .sign div {{ text-align: center; width: 85mm; }}
  .sign .role {{ font-weight: bold; margin-top: 4px; }}
  .sign .hint {{ font-style: italic; font-size: 11pt; }}
  .sign .name {{ font-weight: bold; margin-top: 22mm; }}
  .muted {{ font-size: 11pt; }}
  .toolbar {{ text-align: center; padding: 10px; font-family: Arial, sans-serif; }}
  .toolbar button {{ font-size: 14px; padding: 6px 18px; cursor: pointer; }}
  @media print {{
    body {{ background: #fff; }}
    .page {{ margin: 0; padding: 0; width: auto; min-height: 0; box-shadow: none; }}
    .toolbar {{ display: none; }}
  }}
</style></head>
<body>
<div class="toolbar"><button onclick="window.print()">In báo cáo (Ctrl+P)</button></div>
<div class="page">
  <div class="header">
    <div class="left"><b>{ORGANIZATION}</b><b>{DEPARTMENT}</b><div class="rule"></div></div>
    <div class="right"><b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b><b>Độc lập - Tự do - Hạnh phúc</b><div class="rule"></div></div>
  </div>
  <h1>BÁO CÁO {html.escape(title)}</h1>
  {f'<p class="sub">{html.escape(subtitle)}</p>' if subtitle else ''}
  {f'<p class="sub">{period}</p>' if period else ''}
  {table}
  {summary}
  <div class="sign"><div>
    <div><i>{vietnamese_date_line(created)}</i></div>
    <div class="role">NGƯỜI LẬP BÁO CÁO</div>
    <div class="hint">(Ký, ghi rõ họ tên)</div>
    <div class="name">{creator}</div>
    {creator_code}
  </div></div>
</div>
</body></html>
"""


def write_report(result: ReportResult, creator_name: str, creator_id: Any = None,
                 created: date | None = None, folder: Path | None = None) -> Path:
    """Ghi bản in ra tệp .html (mặc định trong thư mục tạm) và trả về đường dẫn."""
    folder = folder or Path(tempfile.gettempdir()) / "qltv_reports"
    folder.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in result.title)[:80]
    path = folder / f"{safe}_{datetime.now():%Y%m%d_%H%M%S}.html"
    path.write_text(render_html(result, creator_name, created, creator_id), encoding="utf-8")
    return path


def open_print_preview(result: ReportResult, creator_name: str, creator_id: Any = None) -> Path:
    """Ghi bản in và mở bằng trình duyệt mặc định để xem trước / in / lưu PDF."""
    path = write_report(result, creator_name, creator_id)
    webbrowser.open(path.as_uri())
    return path
