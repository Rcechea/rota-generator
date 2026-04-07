import streamlit as st
import datetime
import io
import numpy as np

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

people_text = st.sidebar.text_area(
    "People (one per line):",
    value="\n".join(st.session_state.people_list)
)

areas_text = st.sidebar.text_area(
    "Areas (one per line):",
    value="\n".join(st.session_state.areas_list)
)

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
# ✅ SIDEBAR: Inputs & Buttons
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
def log_write(m):
    log.write(m)


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

        # Convert assignments from names to indices
        hist_assign = []
        for m in history.get("months", []):
            mapping = m["assignment"]
            month_assignment = []
            for p in people:
                area_name = mapping.get(p)
                if area_name == "Sick":
                    month_assignment.append(None)
                elif area_name in areas:
                    month_assignment.append(areas.index(area_name))
                else:
                    month_assignment.append(None)
            hist_assign.append(month_assignment)

        # Display & export
        for i, assignment in enumerate(hist_assign):
            df, styled = build_debug_dataframe(
                people, areas, allowed, assignment, hist_assign[:i]
            )
            st.write(f"### Month {i+1}")
            st.dataframe(styled, height=600)

            buf = io.BytesIO()
            export_debug_matrix(
                buf,
                people,
                areas,
                allowed_matrix=allowed,
                assignment=assignment,
                history_assignments=hist_assign[:i]
            )
            buf.seek(0)

            st.download_button(
                label=f"Download Debug {i+1}",
                data=buf,
                file_name=f"debug_history_month_{i+1}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.success("✅ Rebuilt all debug files!")

    except Exception as e:
        st.error(str(e))
        st.stop()


# =============================================================
# ✅ RUN ROTATION — Sick‑Safe Version
# =============================================================
if generate_btn:
    try:
        people = st.session_state.people_list
        areas = st.session_state.areas_list
        allowed = st.session_state.allowed_matrix

        sick_people = [
            x.strip()
            for x in sick_people_input.replace("\n", ",").split(",")
            if x.strip()
        ]

        # ✅ Full assignment array — sick get None
        final_assignment = [
            None if p in sick_people else None
            for p in people
        ]

        # ✅ Active (non-sick) people
        active_people = [p for p in people if p not in sick_people]
        active_indices = [people.index(p) for p in active_people]

        # Filter matrix for active people
        filtered_allowed = [
            [row[i] for i in active_indices]
            for row in allowed
        ]

        history = load_history()

        current_assignment = [None] * len(active_people)

        st.write("### Download Debug Files")

        for month_step in range(months_to_generate):
            log_write(f"Processing month {month_step+1}...")

            cost_matrix = build_weighted_cost_matrix(
                filtered_allowed, active_people, areas, history
            )

            # Solve
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

            # Map active assignments back to full list
            for local_idx, person_idx in enumerate(active_indices):
                final_assignment[person_idx] = assignment[local_idx]

            # Export debug
            buf = io.BytesIO()
            export_debug_matrix(
                buf,
                people,
                areas,
                allowed_matrix=allowed,
                assignment=final_assignment,
                history_assignments=[
                    [
                        (areas.index(area_name)
                         if area_name in areas else None)
                        for area_name in m["assignment"].values()
                    ]
                    for m in history.get("months", [])
                ]
            )
            buf.seek(0)

            st.download_button(
                label=f"Download Debug Month {month_step+1}",
                data=buf,
                file_name=f"rota_debug_{month_step+1}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Save history (we pass 'Sick' for sick people)
            update_history(history, final_assignment, people, areas)
            save_history(history)

            current_assignment = assignment

        st.success("✅ Rota generation complete!")

    except Exception as e:
        st.error(f"❌ ERROR: {e}")