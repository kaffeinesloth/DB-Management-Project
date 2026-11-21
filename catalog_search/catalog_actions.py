"""Read-only catalogue queries exposed to the shared DOCGIA role."""

from typing import Any, Dict, List

from database import get_connection


def search_catalog(keyword: str = "", available_only: bool = False) -> List[Dict[str, Any]]:
    """Return catalogue copies matching a title, code, author, or category."""
    term = (keyword or "").strip()
    pattern = f"%{term}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT MASACH, ISBN, TENSACH, TACGIA, THELOAI, NGONNGU,
                   NHAXB, COSAN, KE, VITRI
            FROM dbo.v_TraCuuSachDocGia
            WHERE (
                    ? = N''
                    OR MASACH LIKE ?
                    OR ISBN LIKE ?
                    OR TENSACH LIKE ?
                    OR TACGIA LIKE ?
                    OR THELOAI LIKE ?
                  )
              AND (? = 0 OR COSAN = 1)
            ORDER BY TENSACH, MASACH;
            """,
            term, pattern, pattern, pattern, pattern, pattern,
            1 if available_only else 0,
        )
        return [
            {
                "MASACH": row[0],
                "ISBN": row[1],
                "TENSACH": row[2],
                "TACGIA": row[3],
                "THELOAI": row[4],
                "NGONNGU": row[5],
                "NHAXB": row[6] or "",
                "COSAN": bool(row[7]),
                "KE": row[8] or "",
                "VITRI": row[9] or "",
            }
            for row in cursor.fetchall()
        ]
