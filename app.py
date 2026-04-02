import streamlit as st
import datetime
from core.config import load_config, save_config
from core.io import (
    load_allowed_matrix,
    load_last_month
)
from core.history import load_history, save_history, update_history, clear_history
from core.constraints import apply_sickness_constraints
from core.greedy import greedy_assign
from core.backtracking import solve_with_backtracking
from core.optimal import solve_optimal
from core.weights import build_weighted_cost_matrix
from core.debug_export import export_debug_matrix
from core.debug_render import build_debug_dataframe
import os

st.set_page_config(page_title="Rota Generator", layout="wide")

st.title("📋 Rota Generator (Streamlit Version)")

# ---------------------
# Sidebar configuration
# ---------------------

st.sidebar.header("Input Files")

allowed_file = st.sidebar.file_uploader("Allowed Matrix (CSV)")
lastmonth_file = st.sidebar.file_uploader("Last Month Assignment (CSV)")

months_to_generate = st.sidebar.number_input("Generate next N months", min_value=1, max_value=12, value=1)

sick_people_input = st.sidebar.text_area(
    "Sick / Holiday (comma or newline separated)",
    ""
)

st.sidebar.write("---")
generate_btn = st.sidebar.button("Generate Rota")
regen_btn = st.sidebar.button("Regenerate Debug From History")
clear_btn = st.sidebar.button("Clear History")

# -------------
# Log area
# -------------
log = st.empty()
def log_write(msg):
    log.write(msg)


# -------------------------------
# Clear history button action
# -------------------------------
if clear_btn:
    clear_history()
    st.success("✅ History cleared successfully.")
    st.stop()


# -------------------------------
# Regenerate Debug From History
# -------------------------------
if regen_btn:
    try:
        if not allowed_file:
            st.error("Please upload the Allowed Matrix CSV.")
            st.stop()

        allowed = load_allowed_matrix(allowed_file)
        history = load_history()
        people = st.session_state.people_list
        areas  = st.session_state.areas_list

        # Convert stored names -> area indexes per month
        history_assignments = []
        for month in history.get("months", []):
            mapping = month.get("assignment", {})
            assignment = [
                areas.index(mapping[p]) if mapping.get(p) in areas else None
                for p in people
            ]
            history_assignments.append(assignment)

        st.write("## Debug Review From History")

        for i, assignment in enumerate(history_assignments):

            # ✅ Only use history BEFORE this month
            history_before = history_assignments[:i]

            df, styled = build_debug_dataframe(
                people=people,
                areas=areas,
                allowed_matrix=allowed,
                assignment=assignment,
                history_assignments=history_before
            )

            st.write(f"### Month {i+1} Debug View")
            st.dataframe(styled, height=600)

            # Optional download
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = f"debug_regen_month_{i+1}_{timestamp}.xlsx"

            export_debug_matrix(
                debug_path,
                people,
                areas,
                allowed_matrix=allowed,
                assignment=assignment,
                history_assignments=history_before
            )

            with open(debug_path, "rb") as f:
                st.download_button(
                    label=f"Download Month {i+1} Debug File",
                    data=f,
                    file_name=debug_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        st.success("✅ Debug regeneration complete!")

    except Exception as e:
        st.error(f"Error regenerating debug files: {e}")

    st.stop()

    st.sidebar.header("People & Areas Editor")

# Initialize session state on first run
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

# Editable text boxes
people_text = st.sidebar.text_area(
    "People (one per line):",
    value="\n".join(st.session_state.people_list)
)

areas_text = st.sidebar.text_area(
    "Areas (one per line):",
    value="\n".join(st.session_state.areas_list)
)

# Update lists on button press
if st.sidebar.button("Save People & Areas"):
    st.session_state.people_list = [
        p.strip() for p in people_text.split("\n") if p.strip()
    ]
    st.session_state.areas_list = [
        a.strip() for a in areas_text.split("\n") if a.strip()
    ]
    st.sidebar.success("Saved!")


# -------------------------------
# RUN ROTATION
# -------------------------------
if generate_btn:

    try:
        if not (allowed_file and lastmonth_file):
            st.error("Please upload all required CSVs.")
            st.stop()

        log_write("Loading files...")

        allowed = load_allowed_matrix(allowed_file)
        people = st.session_state.people_list
        areas  = st.session_state.areas_list
        last_month = load_last_month(lastmonth_file)

        if len(last_month) == 0:
            last_month = [None] * len(people)

        history = load_history()

        sick_people = [x.strip() for x in sick_people_input.replace("\n", ",").split(",") if x.strip()]

        current_assignment = last_month

        st.write("### Download Debug Files")

        # Run month loop
        for month_step in range(months_to_generate):

            log_write(f"Generating month {month_step + 1}...")

            constrained = apply_sickness_constraints(allowed, people, sick_people)

            cost_matrix = build_weighted_cost_matrix(constrained, people, areas, history)

            # Optimal first
            try:
                assignment = solve_optimal(cost_matrix)
            except:
                try:
                    assignment = greedy_assign(
                        constrained, current_assignment,
                        people, areas, cost_matrix,
                        debug_log=log_write
                    )
                except:
                    assignment = solve_with_backtracking(constrained, current_assignment)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = f"rota_debug_{month_step+1}_{timestamp}.xlsx"

            export_debug_matrix(
                debug_path,
                people,
                areas,
                allowed_matrix=constrained,
                assignment=assignment,
                history_assignments=[
                    [
                        areas.index(area_name)
                        for area_name in m["assignment"].values()
                    ]
                    for m in history.get("months", [])
                ]
            )

            with open(debug_path, "rb") as f:
                st.download_button(
                    label=f"Download Month {month_step+1} Debug File",
                    data=f,
                    file_name=debug_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            update_history(history, assignment, people, areas)
            save_history(history)

            current_assignment = assignment

        st.success("✅ Rota generation complete!")

    except Exception as e:
        st.error(f"❌ ERROR: {e}")