"""
Standalone [STOK] Engine for Workstation (No Docker) & Django Integration.
Drop `stok_service.py` + `sql/StockChecking.sql` + `data/StockChecking_cache.json`
into your friend's Django project or run `python run_local_server.py` directly.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv_if_present(env_path: Path | None = None) -> dict[str, str]:
    target = env_path or (BASE_DIR / ".env")
    out: dict[str, str] = {}
    if not target.exists():
        return out
    for raw_line in target.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        out[key] = val
        if key not in os.environ:
            os.environ[key] = val
    return out


_load_dotenv_if_present()


class StokEngine:
    """
    Executes WhatsApp Bot [STOK] commands:
      - [STOK] 219602 WAFER FLAT
      - [STOK] WAFER STICK
      - [STOK] 219602
    Queries Vertica via `vertica-python` (`sql/StockChecking.sql`) when `DB_ENGINE=vertica`,
    falls back to `data/StockChecking_cache.json` when offline, and sorts items from
    largest to lowest stock quantity.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or BASE_DIR).resolve()
        self.sql_dir = self.base_dir / "sql"
        self.data_dir = self.base_dir / "data"

    def _is_vertica_enabled(self) -> bool:
        return os.getenv("DB_ENGINE", "sqlite_mock").strip().lower() == "vertica"

    def query_vertica(self, sql_query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
        """Connect to Vertica using vertica-python and return (column_names, rows)."""
        import vertica_python

        conn_info: dict[str, Any] = {
            "host": os.getenv("VERTICA_HOST", "127.0.0.1"),
            "port": int(os.getenv("VERTICA_PORT", "5433")),
            "database": os.getenv("VERTICA_DB", "VMart"),
            "user": os.getenv("VERTICA_USER", "dbadmin"),
            "password": os.getenv("VERTICA_PASSWORD", ""),
            "connection_timeout": int(os.getenv("VERTICA_TIMEOUT", "30")),
            "unicode_error": "replace",
        }
        if os.getenv("VERTICA_SSL", "false").strip().lower() in ("1", "true", "yes"):
            conn_info["tlsmode"] = "require"

        with vertica_python.connect(**conn_info) as conn:
            cur = conn.cursor()
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
            cur.execute(sql_query)
            cols = [str(desc[0]).upper() for desc in (cur.description or [])]
            rows = cur.fetchall()
            return cols, rows

    def load_stock_rows(self, wil_filter: str = "", depo_filter: str = "") -> tuple[list[dict[str, Any]], str]:
        """Return (rows, source_mode) from live Vertica or local offline cache."""
        rows: list[dict[str, Any]] = []
        source_mode = "offline_cache"
        sql_path = self.sql_dir / "StockChecking.sql"

        if self._is_vertica_enabled() and sql_path.exists():
            try:
                raw_sql = sql_path.read_text(encoding="utf-8", errors="ignore")
                safe_key = re.sub(r"[^0-9A-Z]", "", f"{wil_filter or '21'}{depo_filter or '9602'}".upper())
                safe_schema = re.sub(r"[^A-Za-z0-9_]", "", os.getenv("VERTICA_SCHEMA", "your_schema"))
                safe_tbl_stok = re.sub(r"[^A-Za-z0-9_]", "", os.getenv("VERTICA_TABLE_STOK", "your_stok_table"))
                safe_tbl_oms = re.sub(r"[^A-Za-z0-9_]", "", os.getenv("VERTICA_TABLE_OMS", "your_oms_table"))
                safe_divisi = re.sub(r"[^A-Za-z0-9_-]", "", os.getenv("VERTICA_DIVISI", "01-DIV"))
                safe_year = re.sub(r"[^0-9,]", "", os.getenv("VERTICA_FILTER_YEAR", "2026")) or "2026"
                safe_month = re.sub(r"[^0-9,]", "", os.getenv("VERTICA_FILTER_MONTH", "11")) or "11"
                raw_excl = [
                    re.sub(r"[^A-Za-z0-9_.\s-]", "", g.strip())
                    for g in os.getenv("VERTICA_EXCLUDED_GROUPS", "NONE").split(",")
                    if g.strip()
                ]
                excl_sql = ", ".join(f"'{g}'" for g in (raw_excl or ["NONE"]))
                rendered_sql = (
                    raw_sql.replace("{{DB_SCHEMA}}", safe_schema)
                    .replace("{{TABLE_STOK}}", safe_tbl_stok)
                    .replace("{{TABLE_OMS}}", safe_tbl_oms)
                    .replace("{{DIVISI_CODE}}", safe_divisi)
                    .replace("{{FILTER_YEAR}}", safe_year)
                    .replace("{{FILTER_MONTH}}", safe_month)
                    .replace("{{EXCLUDED_GROUPS}}", excl_sql)
                    .replace("{{KEY}}", safe_key)
                )
                cols, raw_rows = self.query_vertica(rendered_sql)
                for r in raw_rows:
                    rows.append({cols[i]: r[i] for i in range(min(len(cols), len(r)))})
                if rows:
                    source_mode = "vertica_live"
            except Exception as exc:
                source_mode = f"offline_cache (vertica fallback: {exc.__class__.__name__})"

        if not rows:
            cache_file = self.data_dir / "StockChecking_cache.json"
            if cache_file.exists():
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                if isinstance(cached, list):
                    rows = cached

        if wil_filter or depo_filter:
            filtered = []
            for item in rows:
                w_val = str(item.get("WIL") or "").upper()
                d_val = str(item.get("DEPO") or "").upper()
                w_pre = w_val.split("-", 1)[0].strip()
                d_pre = d_val.split("-", 1)[0].strip()
                if wil_filter and w_pre != wil_filter and wil_filter not in w_val:
                    continue
                if depo_filter and d_pre != depo_filter and depo_filter not in d_val:
                    continue
                filtered.append(item)
            return filtered, source_mode
        return rows, source_mode

    def run_stok_command(self, raw_command: str) -> dict[str, Any]:
        """
        Parse and execute:
          - [STOK] 219602 WAFER FLAT
          - [STOK] WAFER STICK
          - [STOK] 219602
        Returns WhatsApp text formatted from largest to lowest stock + structured category items.
        """
        text = (raw_command or "").strip()
        if text.upper().startswith("[STOK]"):
            arg_str = text[6:].strip()
        elif text.upper().startswith("STOK"):
            arg_str = text[4:].strip()
        else:
            arg_str = text

        wil_filter = ""
        depo_filter = ""
        cat_filter = arg_str

        parts = arg_str.split(None, 1)
        if parts:
            first_tok = parts[0].strip()
            rest_tok = parts[1].strip() if len(parts) > 1 else ""
            if first_tok.isdigit() and len(first_tok) == 6:
                wil_filter = first_tok[:2]
                depo_filter = first_tok[2:]
                cat_filter = rest_tok
            elif first_tok.isdigit() and len(first_tok) == 4:
                depo_filter = first_tok
                cat_filter = rest_tok
            elif first_tok.isdigit() and len(first_tok) == 2:
                wil_filter = first_tok
                cat_filter = rest_tok

        rows, source_mode = self.load_stock_rows(wil_filter, depo_filter)
        cat_upper = re.sub(r"\s+", " ", cat_filter.upper()).strip()
        if cat_upper and cat_upper not in ("ALL", "SEMUA", "TOTAL"):
            cat_noprefix = re.sub(r"^\d+\s*-\s*", "", cat_upper).strip()
            exact_matches = []
            partial_matches = []
            for item in rows:
                kat_raw = str(item.get("KATEGORI") or "").upper().strip()
                kat_np = re.sub(r"^\d+\s*-\s*", "", kat_raw).strip()
                gg_raw = str(item.get("GRUPGAB") or "").upper().strip()
                kel_raw = str(item.get("KELOMPOK") or "").upper().strip()
                if kat_raw == cat_upper or kat_np == cat_noprefix:
                    exact_matches.append(item)
                elif (
                    cat_noprefix in kat_np
                    or kat_np in cat_noprefix
                    or cat_noprefix in gg_raw
                    or cat_noprefix in kel_raw
                ):
                    partial_matches.append(item)
            rows = exact_matches if exact_matches else partial_matches

        if not rows:
            fail_msg = (
                f"Waduh, data stok untuk `{arg_str or '219602'}` tidak ditemukan.\n"
                "Contoh ketik:\n"
                "• [STOK] 219602 WAFER FLAT\n"
                "• [STOK] WAFER STICK"
            )
            return {
                "matched": False,
                "command": raw_command,
                "source_mode": source_mode,
                "depo": "",
                "wil": "",
                "categories": [],
                "total_items": 0,
                "reply_message": fail_msg,
            }

        depo_label = str(rows[0].get("DEPO") or "9602-DEPO CONTOH").strip()
        wil_label = str(rows[0].get("WIL") or "21-WILAYAH UTARA").strip()

        cat_items: dict[str, dict[str, float]] = {}
        for item in rows:
            kat = str(item.get("KATEGORI") or "-").strip()
            item_name = str(item.get("ITEMGB") or "-").strip()
            qty = float(item.get("QTYNETSTOK") or 0.0)
            cat_items.setdefault(kat, {})
            cat_items[kat][item_name] = cat_items[kat].get(item_name, 0.0) + qty

        def _cat_sort_key(kat_str: str) -> tuple[int, str]:
            m_num = re.match(r"^(\d+)\s*-", kat_str)
            return (int(m_num.group(1)) if m_num else 999, kat_str)

        msg_blocks: list[str] = [f"Depo: {depo_label}\nWil: {wil_label}"]
        structured_categories: list[dict[str, Any]] = []
        total_items = 0

        for kat in sorted(cat_items.keys(), key=_cat_sort_key):
            items_map = cat_items[kat]
            # Sort strictly from largest to lowest stock
            sorted_pairs = sorted(
                items_map.items(),
                key=lambda kv: (-math.ceil(round(kv[1], 6)), -kv[1], kv[0]),
            )
            lines = [f"{kat}", "Stok | Item"]
            cat_list: list[dict[str, Any]] = []
            for item_name, raw_qty in sorted_pairs:
                disp_qty = int(math.ceil(round(raw_qty, 6)))
                if disp_qty <= 0:
                    continue
                lines.append(f"{disp_qty} | {item_name}")
                cat_list.append({"stok": disp_qty, "raw_qty": round(raw_qty, 4), "item": item_name})
                total_items += 1
            if cat_list:
                msg_blocks.append("\n".join(lines))
                structured_categories.append({"kategori": kat, "items": cat_list})

        return {
            "matched": True,
            "command": raw_command,
            "source_mode": source_mode,
            "depo": depo_label,
            "wil": wil_label,
            "categories": structured_categories,
            "total_items": total_items,
            "reply_message": "\n\n".join(msg_blocks),
        }
