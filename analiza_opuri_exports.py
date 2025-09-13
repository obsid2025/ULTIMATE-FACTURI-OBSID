import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FOLDER = BASE_DIR / "8_August"
EXPORT1 = DEFAULT_FOLDER / "opuri_export_1.xlsx"
EXPORT2 = DEFAULT_FOLDER / "opuri_export_2.xlsx"
OUT_DIR = BASE_DIR / "build" / "Ultimate_FACTURI"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUT_DIR / "analiza_opuri_exports_report.txt"


OP_CANDIDATE_COLS = [
    "op", "ordin", "ordin de plata", "referinta", "ref", "numar", "document", "nr op", "nr_op",
    "movement_ref", "movement reference", "movement ref",
]

AMOUNT_CANDIDATE_COLS = [
    "suma", "amount", "credit", "debit", "valoare", "value", "import",
]

DATE_CANDIDATE_COLS = [
    "data", "date", "posting date", "transaction date", "book date", "booking date",
    "data operatiunii",
]


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    # Replace Romanian diacritics
    replacements = {
        "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
        "ă": "a", "â": "a", "î": "i",
        "Ș": "s", "Ţ": "t", "Ț": "t", "Ă": "a", "Â": "a", "Î": "i",
        "\u0219": "s", "\u021b": "t",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def load_excel_all_sheets(path: Path) -> Dict[str, pd.DataFrame]:
    xls = pd.ExcelFile(path)
    sheets: Dict[str, pd.DataFrame] = {}
    for name in xls.sheet_names:
        df = xls.parse(name)
        # normalize columns
        df.columns = [norm(str(c)) for c in df.columns]
        sheets[str(name)] = df
    return sheets


def find_first_col(cols: List[str], candidates: List[str]) -> Optional[str]:
    ncols = [norm(c) for c in cols]
    # exact match first
    for cand in candidates:
        if cand in ncols:
            return cols[ncols.index(cand)]
    # then substring match
    for cand in candidates:
        for i, nc in enumerate(ncols):
            if cand in nc:
                return cols[i]
    return None


def find_op_col(cols: List[str]) -> Optional[str]:
    ncols = [norm(c) for c in cols]
    # Prefer columns that mention op and nr/numar
    for i, nc in enumerate(ncols):
        if "op" in nc and ("nr" in nc or "numar" in nc):
            return cols[i]
    # Fallback to columns that look like reference
    for i, nc in enumerate(ncols):
        if "ref" in nc and "movement" not in nc:
            return cols[i]
    # Avoid picking 'data op' for op
    for i, nc in enumerate(ncols):
        if "op" in nc and "data" not in nc:
            return cols[i]
    # generic
    return find_first_col(cols, OP_CANDIDATE_COLS)


def find_amount_col(cols: List[str]) -> Optional[str]:
    ncols = [norm(c) for c in cols]
    for i, nc in enumerate(ncols):
        if any(tok in nc for tok in ["suma", "amount", "credit", "valoare", "value", "import"]):
            return cols[i]
    return find_first_col(cols, AMOUNT_CANDIDATE_COLS)


def find_date_col(cols: List[str]) -> Optional[str]:
    ncols = [norm(c) for c in cols]
    for i, nc in enumerate(ncols):
        if "data" in nc or "date" in nc:
            return cols[i]
    return find_first_col(cols, DATE_CANDIDATE_COLS)


def summarize_file(path: Path) -> Dict:
    result = {"path": str(path), "sheets": []}
    if not path.exists():
        result["error"] = "File not found"
        return result
    sheets = load_excel_all_sheets(path)
    for sname, df in sheets.items():
        info = {
            "sheet": sname,
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "columns": list(df.columns),
        }
        op_col = find_op_col(list(df.columns))
        amt_col = find_amount_col(list(df.columns))
        date_col = find_date_col(list(df.columns))
        info["op_col"] = op_col
        info["amount_col"] = amt_col
        info["date_col"] = date_col

        # quick sample values
        sample = {}
        for key, col in [("op", op_col), ("amount", amt_col), ("date", date_col)]:
            if col and col in df.columns and not df.empty:
                sample_vals = df[col].dropna().head(5).tolist()
                sample[key] = [str(v) for v in sample_vals]
        if sample:
            info["samples"] = sample
        result["sheets"].append(info)
    return result


def extract_keys(df: pd.DataFrame, op_col: Optional[str], amt_col: Optional[str], date_col: Optional[str]) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    if op_col and op_col in df.columns:
        out["op_key"] = df[op_col].astype(str).str.strip()
    else:
        out["op_key"] = pd.NA
    if amt_col and amt_col in df.columns:
        out["amount"] = pd.to_numeric(df[amt_col], errors="coerce")
    else:
        out["amount"] = pd.NA
    if date_col and date_col in df.columns:
        out["date"] = pd.to_datetime(df[date_col], errors="coerce")
    else:
        out["date"] = pd.NaT
    return out


def detect_duplicates_across(files: List[Tuple[Path, Dict[str, pd.DataFrame]]]) -> Dict:
    # Build combined index on (op_key, amount, date)
    combined = []
    meta_rows = []
    for fpath, sheets in files:
        for sname, df in sheets.items():
            op_col = find_op_col(list(df.columns))
            amt_col = find_amount_col(list(df.columns))
            date_col = find_date_col(list(df.columns))
            keys = extract_keys(df, op_col, amt_col, date_col)
            keys["source_file"] = str(fpath.name)
            keys["sheet"] = sname
            combined.append(keys)
            meta_rows.append({
                "file": str(fpath.name), "sheet": sname, "rows": len(df),
                "op_col": op_col, "amount_col": amt_col, "date_col": date_col
            })
    if not combined:
        return {"error": "No data"}
    all_df = pd.concat(combined, ignore_index=True)
    # consider duplicates by exact tuple match, with tolerance on amount of 0.01
    all_df["amount_rounded"] = pd.to_numeric(all_df["amount"], errors="coerce").round(2)
    # define a key that ignores small date-time variations (date only)
    all_df["date_only"] = pd.to_datetime(all_df["date"], errors="coerce").dt.date
    key_cols = ["op_key", "amount_rounded", "date_only"]
    dup_mask = all_df.duplicated(subset=key_cols, keep=False)
    dups = all_df.loc[dup_mask].copy()
    # Also compute per-file duplicates
    per_file_dups = all_df.groupby(["source_file"]).apply(
        lambda g: int(g.duplicated(subset=key_cols, keep=False).sum())
    )
    # Cross-file duplicates: same key appearing in both files
    by_file = {
        fname: set(map(tuple, g[key_cols].dropna().values.tolist()))
        for fname, g in all_df.groupby("source_file")
    }
    file_names = list(by_file.keys())
    cross_overlap = set()
    if len(file_names) >= 2:
        cross_overlap = by_file[file_names[0]].intersection(by_file[file_names[1]])

    return {
        "total_rows": int(len(all_df)),
        "duplicate_rows_total": int(len(dups)),
        "per_file_duplicate_rows": {k: int(v) for k, v in per_file_dups.to_dict().items()},
        "cross_file_overlap_keys": list(cross_overlap),
        "key_columns": key_cols,
        "meta": meta_rows,
    }


def main() -> None:
    lines: List[str] = []
    lines.append("Analiza opuri_export_*.xlsx")
    lines.append("")

    summary1 = summarize_file(EXPORT1)
    summary2 = summarize_file(EXPORT2)

    for idx, summary in enumerate([summary1, summary2], start=1):
        lines.append(f"File {idx}: {summary.get('path')}")
        if "error" in summary:
            lines.append(f"  ERROR: {summary['error']}")
            lines.append("")
            continue
        for sh in summary["sheets"]:
            lines.append(f"  - Sheet: {sh['sheet']} | rows={sh['rows']} cols={sh['cols']}")
            lines.append(f"    columns: {sh['columns']}")
            lines.append(f"    inferred: op={sh.get('op_col')} amount={sh.get('amount_col')} date={sh.get('date_col')}")
            if "samples" in sh:
                lines.append(f"    samples: {sh['samples']}")
        lines.append("")

    # Load dataframes for duplicate/overlap detection
    files_loaded: List[Tuple[Path, Dict[str, pd.DataFrame]]] = []
    for p in [EXPORT1, EXPORT2]:
        if p.exists():
            files_loaded.append((p, load_excel_all_sheets(p)))
    overlap_info = detect_duplicates_across(files_loaded)

    if "error" in overlap_info:
        lines.append(f"Overlap analysis error: {overlap_info['error']}")
    else:
        lines.append("Overlap & duplicate analysis:")
        lines.append(f"  total_rows: {overlap_info['total_rows']}")
        lines.append(f"  duplicate_rows_total: {overlap_info['duplicate_rows_total']}")
        lines.append(f"  per_file_duplicate_rows: {overlap_info['per_file_duplicate_rows']}")
        lines.append(f"  key_columns: {overlap_info['key_columns']}")
        cross = overlap_info.get("cross_file_overlap_keys", [])
        lines.append(f"  cross_file_overlap_keys_count: {len(cross)}")
        preview = list(cross)[:10]
        if preview:
            lines.append(f"  sample_overlap_keys (first 10): {preview}")
        lines.append("")

        # derive a conclusion: superset vs partial overlap
        by_file_counts = {}
        if files_loaded:
            # rebuild the per-file key sets to check containment
            all_df_list = []
            by_file_sets = {}
            for fpath, sheets in files_loaded:
                combined = []
                for sname, df in sheets.items():
                    op_col = find_op_col(list(df.columns))
                    amt_col = find_amount_col(list(df.columns))
                    date_col = find_date_col(list(df.columns))
                    keys = extract_keys(df, op_col, amt_col, date_col)
                    keys["amount_rounded"] = pd.to_numeric(keys["amount"], errors="coerce").round(2)
                    keys["date_only"] = pd.to_datetime(keys["date"], errors="coerce").dt.date
                    combined.append(keys[["op_key", "amount_rounded", "date_only"]])
                if combined:
                    cur = pd.concat(combined, ignore_index=True)
                    key_set = set(map(tuple, cur.dropna().values.tolist()))
                else:
                    key_set = set()
                by_file_sets[fpath.name] = key_set
                by_file_counts[fpath.name] = len(key_set)
            if len(by_file_sets) == 2:
                f1, f2 = list(by_file_sets.keys())
                only_f1 = by_file_sets[f1] - by_file_sets[f2]
                only_f2 = by_file_sets[f2] - by_file_sets[f1]
                lines.append("Containment check:")
                lines.append(f"  unique_keys_{f1}: {len(by_file_sets[f1])}")
                lines.append(f"  unique_keys_{f2}: {len(by_file_sets[f2])}")
                lines.append(f"  only_in_{f1}: {len(only_f1)}")
                lines.append(f"  only_in_{f2}: {len(only_f2)}")
                if not only_f1 and by_file_sets[f1]:
                    lines.append(f"  Observation: {f1} appears to be a subset of {f2}.")
                if not only_f2 and by_file_sets[f2]:
                    lines.append(f"  Observation: {f2} appears to be a subset of {f1}.")

    text = "\n".join(lines)
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback for cp1252 consoles: write UTF-8 bytes with replacement
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    REPORT_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
