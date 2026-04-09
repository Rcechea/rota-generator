import streamlit as st
import datetime
import io
import numpy as np
import json
import zipfile
from io import BytesIO

from core.history import load_history, save_history, update_history, clear_history
from core.greedy import greedy_assign
from core.backtracking import solve_with_backtracking
from core.optimal import solve_optimal
from core.weights import build_weighted_cost_matrix
from core.debug_export import export_debug_matrix
from core.debug_render import build_debug_dataframe


# -------------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------------
st.set_page_config(page_title="Rota Generator", layout="wide")
st.title("📋 Rota Generator (Streamlit Version)")


# =============================================================
# ✅ PEOPLE & AREAS INITIALIZATION
# =============================================================
st.sidebar.header("People & Areas Editor")

if "people_list" not in st.session_state:
    st.session_state.people_list = ["Person 1", "Person 2", "Person 3",
                                    "Person 4", "Person 5", "Person 6"]

if "areas_list" not in st.session_state:
    st.session_state.areas_list = ["Area 1", "Area 2", "Area 3",
                                   "Area 4", "Area 5", "Area 6"]


def ensure_matrix_matches_shape():
    people = st.session_state.people_list
    areas = st.session_state.areas_list
    rows = len(areas)
    cols = len(people)

    if "allowed_matrix" not in st.session_state:
        st.session_state.allowed_matrix = np.ones((rows, cols), dtype=int).tolist()
        return

    matrix = st.session_state.allowed_matrix
    old_rows = len(matrix)
    old_cols = len(matrix[0]) if old_rows else 0

    if rows != old_rows or cols != old_cols:
        new_matrix = np.ones((rows, cols), dtype=int).tolist()
        for r in range(min(rows, old_rows)):
            for c in range(min(cols, old_cols)):
                new_matrix[r][c] = matrix[r][c]
        st.session_state.allowed_matrix = new_matrix


ensure_matrix_matches_shape()


# =============================================================
# ✅ PEOPLE & AREAS TEXT INPUT
# =============================================================
people_text = st.sidebar.text_area(
    "People (one per line):", value="\n".join(st.session_state.people_list)
)

areas_text = st.sidebar.text_area(
    "Areas (one per line):", value="\n".join(st.session_state.areas_list)
)

if st.sidebar.button("Save People & Areas"):
    st.session_state.people_list = [p.strip() for p in people_text.split("\n") if p.strip()]
    st.session_state.areas_list = [a.strip() for a in areas_text.split("\n") if a.strip()]
    ensure_matrix_matches_shape()
    st.sidebar.success("✅ Saved people and areas!")


# =============================================================
# ✅ IMPORT / EXPORT PEOPLE, AREAS, MATRIX
# =============================================================
st.sidebar.write("---")
st.sidebar.subheader("Import / Export People & Areas & Matrix")

upload_config = st.sidebar.file_uploader("Import JSON", type="json")

if upload_config is not None:
    data = json.load(upload_config)

    if "people" in data and "areas" in data:
        st.session_state.people_list = data["people"]
        st.session_state.areas_list = data["areas"]

        if "allowed_matrix" in data:
            st.session_state.allowed_matrix = data["allowed_matrix"]
        else:
            st.session_state.allowed_matrix = np.ones(
                (len(data["areas"]), len(data["people"])), dtype=int
            ).tolist()

        ensure_matrix_matches_shape()
        st.sidebar.success("✅ JSON imported successfully!")
    else:
        st.sidebar.error("❌ Invalid JSON (must include people & areas).")

export_data = {
    "people": st.session_state.people_list,
    "areas": st.session_state.areas_list,
    "allowed_matrix": st.session_state.allowed_matrix
}

st.sidebar.download_button(
    label="Download JSON",
    data=json.dumps(export_data, indent=4).encode("utf-8"),
    file_name="people_areas_matrix.json",
    mime="application/json"
)


# =============================================================
# ✅ MATRIX TABLE
# =============================================================
st.write("## Allowed Assignments Matrix")

people = st.session_state.people_list
areas = st.session_state.areas_list
matrix = st.session_state.allowed_matrix

cols = st.columns(len(people) + 1)
cols[0].write("**Area / Person**")

for i, p in enumerate(people):
    cols[i + 1].write(f"**{p}**")

for r, area in enumerate(areas):
    row = st.columns(len(people) + 1)
    row[0].write(area)
    for c, person in enumerate(people):
        key = f"matrix_{r}_{c}"
        checked = matrix[r][c] == 1
        new_val = row[c + 1].checkbox("", value=checked, key=key)
        matrix[r][c] = 1 if new_val else 0

st.session_state.allowed_matrix = matrix


# =============================================================
# ✅ ROTATION SETTINGS
# =============================================================
st.sidebar.write("---")
st.sidebar.header("Generation Settings")

months_to_generate = st.sidebar.number_input(
    "Generate next N months", min_value=1, max_value=12, value=1
)

sick_people_input = st.sidebar.text_area(
    "Sick / Holiday (one per line or comma separated)", ""
)

run_btn = st.sidebar.button("Generate Rota")
regen_btn = st.sidebar.button("Regenerate Debug From History")
clear_btn = st.sidebar.button("Clear History")


# =============================================================
# ✅ CLEAR HISTORY
# =============================================================
if clear_btn:
    clear_history()
    st.success("✅ History cleared!")
    st.stop()


# =============================================================
# ✅ REGENERATE DEBUG FROM HISTORY — FIXED ZIP ORDER
# =============================================================
if regen_btn:
    history = load_history()
    people = st.session_state.people_list
    areas = st.session_state.areas_list
    allowed = st.session_state.allowed_matrix

    st.write("## Debug Files From History")

    # Build ZIP first
    zip_buffer = BytesIO()
    zipf = zipfile.ZipFile(zip_buffer, mode="w")

    assignments = []
    for m in history.get("months", []):
        mapping = m["assignment"]
        row = []
        for p in people:
            area = mapping.get(p)
            row.append(areas.index(area) if area in areas else None)
        assignments.append(row)

    # Build all excel files into ZIP
    for i, asg in enumerate(assignments):
        buf = io.BytesIO()
        export_debug_matrix(
            buf,
            people,
            areas,
            allowed_matrix=allowed,
            assignment=asg,
            history_assignments=assignments[:i]
        )
        buf.seek(0)
        zipf.writestr(f"debug_history_month_{i+1}.xlsx", buf.read())

    zipf.close()
    zip_buffer.seek(0)

    # ✅ ZIP download button ABOVE table output
    st.download_button(
        "⬇ Download ALL History Debug Files (ZIP)",
        zip_buffer,
        file_name="history_debug_all_months.zip",
        mime="application/zip"
    )

    # ✅ NOW show the preview tables
    for i, asg in enumerate(assignments):
        df, styled = build_debug_dataframe(
            people, areas, allowed, asg, assignments[:i]
        )
        st.write(f"### Month {i+1}")
        st.dataframe(styled, height=500)

    st.success("✅ Debug regenerated!")


# =============================================================
# ✅ GENERATE NEW ROTA — FIXED ZIP ORDER
# =============================================================
if run_btn:
    try:
        people = st.session_state.people_list
        areas = st.session_state.areas_list
        allowed = st.session_state.allowed_matrix

        sick = [s.strip() for s in sick_people_input.replace("\n", ",").split(",") if s.strip()]

        final_assignment = [None] * len(people)

        active_people = [p for p in people if p not in sick]
        active_idx = [people.index(p) for p in active_people]

        filtered_matrix = [[row[i] for i in active_idx] for row in allowed]

        history = load_history()
        current_assignment = [None] * len(active_people)

        st.write("## Debug Downloads")

        # ZIP container
        zip_buffer = BytesIO()
        zipf = zipfile.ZipFile(zip_buffer, mode="w")

        for step in range(months_to_generate):

            cost = build_weighted_cost_matrix(
                filtered_matrix, active_people, areas, history
            )

            # Solvers in order
            try:
                assignment = solve_optimal(cost)
            except:
                try:
                    assignment = greedy_assign(
                        filtered_matrix,
                        current_assignment,
                        active_people,
                        areas,
                        cost
                    )
                except:
                    assignment = solve_with_backtracking(
                        filtered_matrix,
                        current_assignment
                    )

            # Map back to full list
            for j, real_idx in enumerate(active_idx):
                final_assignment[real_idx] = assignment[j]

            # Build excel output
            buf = io.BytesIO()
            export_debug_matrix(
                buf, people, areas,
                allowed_matrix=allowed,
                assignment=final_assignment,
                history_assignments=[]
            )
            buf.seek(0)

            zipf.writestr(f"rota_debug_month_{step+1}.xlsx", buf.read())

            update_history(history, final_assignment, people, areas)
            save_history(history)

            current_assignment = assignment

        zipf.close()
        zip_buffer.seek(0)

        # ✅ Download button NOW — after zip is filled
        st.download_button(
            "⬇ Download ALL Generated Debug Files (ZIP)",
            zip_buffer,
            file_name="rota_debug_all_months.zip",
            mime="application/zip"
        )

        st.success("✅ Rota generation complete!")

    except Exception as e:
        st.error(f"❌ ERROR: {e}")