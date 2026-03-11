"""
Generate SQL to:
1. Add is_have_audio column to public.books_list
2. Update is_have_audio per book based on status Excel file

DONE    -> 'yes'
PARTIAL -> 'partial'
PENDING -> 'no'
"""
import glob
import sys
from pathlib import Path

import openpyxl

STATUS_MAP = {"DONE": "yes", "PARTIAL": "partial", "PENDING": "no"}

BASE_DIR = Path(__file__).parent

# Find the status Excel file (latest by name)
excel_files = sorted(BASE_DIR.glob("status_*.xlsx"))
if not excel_files:
    print("ERROR: No status_*.xlsx file found.")
    sys.exit(1)

excel_path = excel_files[-1]
print(f"Reading: {excel_path.name}")

wb = openpyxl.load_workbook(excel_path)
ws = wb.active

lines = [
    "-- Add is_have_audio column to books_list",
    "ALTER TABLE public.books_list ADD COLUMN IF NOT EXISTS is_have_audio VARCHAR(10) DEFAULT 'no';",
    "",
    "-- Update is_have_audio based on audio processing status",
    f"-- Source: {excel_path.name}",
    "",
]

counts = {"yes": 0, "partial": 0, "no": 0}

for row in ws.iter_rows(min_row=2, values_only=True):
    book_id = row[1]
    status = row[3]
    if not book_id or not status:
        continue
    val = STATUS_MAP.get(str(status).upper(), "no")
    lines.append(f"UPDATE public.books_list SET is_have_audio = '{val}' WHERE id = {book_id};")
    counts[val] += 1

output = "\n".join(lines)
out_path = BASE_DIR / "update_is_have_audio.sql"
out_path.write_text(output, encoding="utf-8")

print(f"Saved: {out_path.name}")
print(f"  yes (DONE)    : {counts['yes']}")
print(f"  partial        : {counts['partial']}")
print(f"  no (PENDING)   : {counts['no']}")
print(f"  Total UPDATEs  : {sum(counts.values())}")
