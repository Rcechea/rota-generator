# core/debug_export.py
"""
Enhanced debug matrix export supporting:
- Yellow  = current assignment
- Black   = forbidden
- White   = allowed but unused
- 12 distinct recency colours (1–12 months ago)
- Cell values show "X" or "✓ (X)" where X = months since last used
"""

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Font

# 12–month hue‑based colour scale (highly distinguishable)
RECENCY_COLORS = [
    "A7D8FF",  # 1 month - light blue
    "73E0C1",  # 2 - teal
    "7CF37A",  # 3 - green
    "C6F56F",  # 4 - lime
    "E4F55B",  # 5 - yellow‑green
    "FFD753",  # 6 - yellow-orange
    "FFB870",  # 7 - peach
    "FF8A8A",  # 8 - light red
    "FF5757",  # 9 - red
    "AC6BFF",  # 10 - purple
    "9457D6",  # 11 - violet
    "6133A1",  # 12+ - deep purple
]

BLACK  = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
YELLOW = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
WHITE  = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")


def export_debug_matrix(
    path,
    people,
    areas,
    allowed_matrix,
    assignment,
    history_assignments
):
    wb = Workbook()
    ws = wb.active
    ws.title = "DebugMatrix"

    # Header
    ws.cell(1, 1, "Area").font = Font(bold=True)
    for col, person in enumerate(people, start=2):
        c = ws.cell(1, col, person)
        c.font = Font(bold=True)
        ws.column_dimensions[c.column_letter].width = 18

    # Reverse history so index 0 = last month
    rev_hist = list(reversed(history_assignments))

    for row, area in enumerate(areas, start=2):
        ws.cell(row, 1, area).font = Font(bold=True)

        for col, person in enumerate(people, start=2):
            area_idx = row - 2
            person_idx = col - 2
            cell = ws.cell(row, col)

            # Forbidden
            if allowed_matrix[area_idx][person_idx] == 0:
                cell.fill = BLACK
                continue

            # Determine past recency
            past_age = None
            for i, month in enumerate(rev_hist):
                if person_idx < len(month) and month[person_idx] == area_idx:
                    past_age = i + 1
                    break


            
            # SICK: assignment = None
            if assignment[person_idx] is None:
                cell.value = "SICK"
                cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99",
                                        fill_type="solid")  # light yellow
                continue
                

            # PAST assignment (not current)
            if past_age is not None:
                idx = min(past_age - 1, len(RECENCY_COLORS) - 1)
                color = RECENCY_COLORS[idx]
                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                cell.value = str(past_age)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                continue

            # Allowed & unused
            cell.value = ""
            cell.fill = WHITE
            cell.alignment = Alignment(horizontal="center", vertical="center")

    wb.save(path)