import streamlit as st
import datetime
import io
import numpy as np
import json

from core.history import load_history, save_history, update_history, clear_history
from core.constraints import apply_sickness_constraints
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
# ✅ PEOPLE & AREAS – FIRST IN SIDEBAR
# =============================================================
st.sidebar.header("People & Areas Editor")

# Initialize defaults
if "people_list" not in st.session_state:
    st.session_state.people_list = [
        "Sharon Mckeown",
        "Hetal Bari",
        "Dorota Szyca",
        "Jagoda Ndreca",
        "Laszlo Hevesi",
        "Inbound vacancy",
        "Zuzana Korpova",
        "Marius Gutae",
        "Cristina Zamfira"
    ]

if "areas_list" not in st.session_state:
    st.session_state.areas_list = [
        "Receiving/Racking",
        "Yard/Car Park",
        "Canteen",
        "HR Office",
        "Ground Floor",
        "First Floor",
        "Second Floor A",
        "Second Floor B",
        "Third Floor"
    ]

# Text boxes
people_text = st.sidebar.text_area(
    "People (one per line):",
    value="\n".join(st.session_state.people_list)
)

areas_text = st.sidebar.text_area(
    "Areas (one per line):",
    value="\n".join(st.session_state.areas_list)
)

# Save button
if st.sidebar.button("Save People & Areas"):
    new_people = [p.strip() for p in people_text.split("\n") if p.strip()]
    new_areas = [a.strip() for a in areas_text.split("\n") if a.strip()]

    st.session_state.people_list = new_people
    st.session_state.areas_list = new_areas

    st.session_state.allowed_matrix = np.ones(
        (len(new_areas), len(new_people)), dtype=int
    ).tolist()

    st.sidebar.success("Saved!")


# =============================================================
# ✅ IMPORT / EXPORT (ALWAYS VISIBLE)
# =============================================================
st.sidebar.write("---")
st.sidebar.subheader("Import / Export People & Areas")

# Import JSON
upload_config = st.sidebar.file_uploader("Import People & Areas (JSON)", type="json")

if upload_config is not None:
    data = json.load(upload_config)

    if "people" in data and "areas" in data:
        st.session_state.people_list = data["people"]
        st.session_state.areas_list = data["areas"]

        st.session_state.allowed_matrix = np.ones(
            (len(data["areas"]), len(data["people"])), dtype=int
        ).tolist()

        st.sidebar.success("✅ Imported People & Areas successfully!")
    else:
        st.sidebar.error("Invalid JSON format. Must contain 'people' and 'areas'.")

# Export JSON
export_data = {
    "people": st.session_state.people_list,
    "areas": st.session_state.areas_list
}

export_bytes = json.dumps(export_data, indent=4).encode("utf-8")

st.sidebar.download_button(
    label="Download People & Areas",
    data=export_bytes,
    file_name="people_areas.json",
    mime="application/json"
)


# =============================================================
# ✅ ALLOWED MATRIX – INTERACTIVE CHECKBOX GRID
# =============================================================
st.write("## Allowed Assignments Matrix")

people = st.session_state.people_list
areas = st.session_state.areas_list

num_people = len(people)
num_areas = len(areas)

if "allowed_matrix" not in st.session_state:
    st.session_state.allowed_matrix = np.ones(
        (num_areas, num_people), dtype=int
    ).tolist()

matrix = st.session_state.allowed_matrix

cols = st.columns(num_people + 1)
cols[0].write("**Area / Person**")
for idx, p in enumerate(people):
    cols[idx + 1].write(f"**{p}**")

for a_idx, area in enumerate(areas):
    row = st.columns(num_people + 1)
    row[0].write(f"**{area}**")
    for p_idx, person in enumerate(people):
        key = f"a{a_idx}_p{p_idx}"
        val = matrix[a_idx][p_idx] == 1
        new_val = row[p_idx + 1].checkbox("", value=val, key=key)
        matrix[a_idx][p_idx] = 1 if new_val else 0

st.session_state.allowed_matrix = matrix


# =============================================================
# ✅ SIDEBAR: Input Buttons
# =============================================================
st.sidebar.header("Input Settings")

months_to_generate = st.sidebar.number_input(
    "Generate next N months", min_value=1, max_value=12, value=1
)

sick_people_input = st.sidebar.text_area(
    "Sick / Holiday (comma or newline separated)", ""
)

st.sidebar.write("---")
generate_btn = st.sidebar.button("Generate Rota")
regen_btn = st.sidebar.button("Regenerate Debug From History")
clear_btn = st.sidebar.button("Clear History")


# =============================================================
# ✅ LOG AREA
# =============================================================
log = st.empty()
def log_write(msg):
    log.write(msg)


# =============================================================
# ✅ CLEAR HISTORY
# =============================================================
if clear_btn:
    clear_history()
    st.success("✅ History cleared!")
    st.stop()


# =============================================================
# ✅ REGENERATE DEBUG FROM HISTORY
# =============================================================
if regen_btn:
    try:
        people = st.session_state.people_list
        areas = st.session_state.areas_list
        allowed = st.session_state.allowed_matrix
        history = load_history()

        st.write("## Debug Review From History")

        hist_assign = []
        for m in history.get("months", []):
            mapping = m["assignment"]
            assignment = []
            for p in people:
                area_name = mapping.get(p)
                if area_name == "Sick":
                    assignment.append(None)
                elif area_name in areas:
                    assignment.append(areas.index(area_name))
                else:
                    assignment.append(None)
            hist_assign.append(assignment)

        for i, asg in enumerate(hist_assign):
            df, styled = build_debug_dataframe(
                people, areas, allowed, asg, hist_assign[:i]
            )
            st.write(f"### Month {i+1}")
            st.dataframe(styled, height=600)

            buf = io.BytesIO()
            export_debug_matrix(
                buf,
                people,
                areas,
                allowed_matrix=allowed,
                assignment=asg,
                history_assignments=hist_assign[:i]
            )
            buf.seek(0)

            st.download_button(
                f"Download Debug {i+1}",
                buf,
                f"debug_history_month_{i+1}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.success("✅ Debug regenerated!")

    except Exception as e:
        st.error(str(e))
        st.stop()


# =============================================================
# ✅ RUN ROTATION (Sick‑Safe)
# =============================================================
if generate_btn:
    try:
        people = st.session_state.people_list
        areas = st.session_state.areas_list
        allowed = st.session_state.allowed_matrix

        sick_people = [
            s.strip()
            for s in sick_people_input.replace("\n", ",").split(",")
            if s.strip()
        ]

        final_assignment = [None] * len(people)

        active_people = [p for p in people if p not in sick_people]
        active_indices = [people.index(p) for p in active_people]

        filtered_allowed = [
            [row[i] for i in active_indices]
            for row in allowed
        ]

        history = load_history()
        current_assignment = [None] * len(active_people)

        st.write("### Download Debug Files")

        for step in range(months_to_generate):

            log_write(f"Processing month {step+1}...")

            cost_matrix = build_weighted_cost_matrix(
                filtered_allowed, active_people, areas, history
            )

            # Try solvers in order
            try:
                assignment = solve_optimal(cost_matrix)
            except:
                try:
                    assignment = greedy_assign(
                        filtered_allowed,
                        current_assignment,
                        active_people,
                        areas,
                        cost_matrix,
                        debug_log=log_write
                    )
                except:
                    assignment = solve_with_backtracking(
                        filtered_allowed, current_assignment
                    )

            # Map to full assignment
            for loc, real_idx in enumerate(active_indices):
                final_assignment[real_idx] = assignment[loc]

            buf = io.BytesIO()
            export_debug_matrix(
                buf, people, areas,
                allowed_matrix=allowed,
                assignment=final_assignment,
                history_assignments=[
                    [
                        areas.index(a) if a in areas else None
                        for a in m["assignment"].values()
                    ]
                    for m in history.get("months", [])
                ]
            )
            buf.seek(0)

            st.download_button(
                f"Download Debug Month {step+1}",
                buf,
                f"rota_debug_{step+1}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            update_history(history, final_assignment, people, areas)
            save_history(history)

            current_assignment = assignment

        st.success("✅ Rota generation complete!")

    except Exception as e:
        st.error(f"❌ ERROR: {e}")