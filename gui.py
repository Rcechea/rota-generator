# gui.py
"""
PySimpleGUI interface for the rota solver.
"""

import PySimpleGUI as sg
import datetime
from core.config import load_config, save_config
from core.io import (
    load_allowed_matrix,
    load_people,
    load_areas,
    load_last_month,
    export_csv,
    export_excel
)
from core.history import load_history, save_history, update_history
from core.constraints import apply_sickness_constraints
from core.greedy import greedy_assign
from core.backtracking import solve_with_backtracking
from core.optimal import solve_optimal
from core.weights import build_weighted_cost_matrix
from core.debug_export import export_debug_matrix


def log(window, message):
    """Append text to the scrolling log box."""
    window["LOG"].print(message)


def launch_gui():

    sg.theme("SystemDefault")
    cfg = load_config()

    layout = [

    [sg.Text("Allowed Matrix (CSV)")],
    [sg.Input(key="ALLOWED", default_text=cfg.get("allowed", "")), sg.FileBrowse()],

    [sg.Text("People (CSV)")],
    [sg.Input(key="PEOPLE", default_text=cfg.get("people", "")), sg.FileBrowse()],

    [sg.Text("Areas (CSV)")],
    [sg.Input(key="AREAS", default_text=cfg.get("areas", "")), sg.FileBrowse()],

    [sg.Text("Last Month Assignment (CSV)")],
    [sg.Input(key="LASTMONTH", default_text=cfg.get("lastmonth", "")), sg.FileBrowse()],

    [sg.Text("Generate next N months:")],
    [sg.Spin([i for i in range(1, 13)], initial_value=1, key="MONTHS")],

    [sg.Text("Mark sick/holiday:")],
    [sg.Multiline(key="SICKLIST", size=(40, 3))],

    [sg.Button("Generate Rota")],
    [sg.Button("Regenerate Debug From History")],
    [sg.Button("Clear History"), sg.Button("Exit")],

    [sg.Frame("Log Output", [
        [sg.Multiline(key="LOG", size=(80, 20), autoscroll=True, disabled=True)]
    ])],
]

    window = sg.Window("Rota Generator", layout, finalize=True)

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "Exit"):
            break
        if event == "Clear History":
            try:
                from core.history import clear_history
                clear_history()
                log(window, "History cleared successfully.")
            except Exception as e:
                log(window, f"ERROR clearing history: {e}")
            continue
        if event == "Regenerate Debug From History":
            try:
                history = load_history()
                people = load_people(values["PEOPLE"])
                areas = load_areas(values["AREAS"])
                allowed = load_allowed_matrix(values["ALLOWED"])

                # Build a list of assignments per month
                history_assignments = []
                for month in history.get("months", []):
                    assign = []
                    mapping = month.get("assignment", {})
                    for p in people:
                        area = mapping.get(p)
                        if area is None:
                            assign.append(None)
                        else:
                            assign.append(areas.index(area))
                    history_assignments.append(assign)

                # Export debug sheet per month
                for i, assignment in enumerate(history_assignments):
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    debug_path = f"debug_regen_month_{i+1}_{timestamp}.xlsx"
                    export_debug_matrix(
                        debug_path,
                        people,
                        areas,
                        allowed,
                        assignment,
                        history_assignments[:i]  # history BEFORE this month
                    )
                    log(window, f"Regenerated Debug File: {debug_path}")

            except Exception as e:
                log(window, f"ERROR during regeneration: {e}")

            continue

        if event == "Generate Rota":

            # Save file paths to config.json
            new_cfg = {
                "allowed": values["ALLOWED"],
                "people": values["PEOPLE"],
                "areas": values["AREAS"],
                "lastmonth": values["LASTMONTH"]
            }
            save_config(new_cfg)

            try:
                log(window, "Loading inputs...")

                # Load inputs
                allowed = load_allowed_matrix(values["ALLOWED"])
                people = load_people(values["PEOPLE"])
                areas = load_areas(values["AREAS"])
                last_month = load_last_month(values["LASTMONTH"])

                if len(last_month) == 0:
                    last_month = [None] * len(people)

                history = load_history()

                sick_people = [
                    name.strip() for name in values["SICKLIST"].replace("\n", ",").split(",")
                    if name.strip()
                ]

                months_to_generate = int(values["MONTHS"])
                current_assignment = last_month

                log(window, f"Sick/Holiday list: {sick_people}")

                # ============================================================
                # MAIN MONTH LOOP
                # ============================================================
                for month_step in range(months_to_generate):

                    log(window, f"\n=== Generating month {month_step + 1} ===")

                    # Apply sickness
                    constrained_matrix = apply_sickness_constraints(
                        allowed, people, sick_people
                    )

                    # Build weights
                    cost_matrix = build_weighted_cost_matrix(
                        constrained_matrix, people, areas, history
                    )

                    # ========================================================
                    # 1️⃣ PRIMARY: OPTIMAL SOLVER
                    # ========================================================
                    log(window, "Trying optimal solver...")
                    try:
                        assignment = solve_optimal(cost_matrix)
                        log(window, "Optimal solver succeeded.")

                    except Exception as e_opt:
                        log(window, f"Optimal solver failed: {e_opt}")
                        log(window, "Trying Weighted Greedy...")

                        # ====================================================
                        # 2️⃣ FALLBACK: WEIGHTED GREEDY
                        # ====================================================
                        try:
                            assignment = greedy_assign(
                                constrained_matrix,
                                current_assignment,
                                people,
                                areas,
                                cost_matrix,
                                debug_log=lambda m: log(window, m)
                            )
                            log(window, "Greedy solver succeeded.")

                        except Exception as e_greedy:
                            log(window, f"Greedy failed: {e_greedy}")
                            log(window, "Trying Backtracking...")

                            # ====================================================
                            # 3️⃣ FINAL FALLBACK: BACKTRACKING
                            # ====================================================
                            assignment = solve_with_backtracking(
                                constrained_matrix,
                                current_assignment
                            )
                            log(window, "Backtracking succeeded.")

                    # Export
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    csv_path = f"rota_{month_step+1}_{timestamp}.csv"
                    excel_path = f"rota_{month_step+1}_{timestamp}.xlsx"


                    # Debug matrix export
                    debug_path = f"rota_debug_{month_step+1}_{timestamp}.xlsx"
                    history_assignments_list = [m["assignment"] for m in history.get("months", [])]

                    export_debug_matrix(
                        debug_path,
                        people=people,
                        areas=areas,
                        allowed_matrix=constrained_matrix,
                        assignment=assignment,
                        history_assignments=[
                            [areas.index(area_name) for _, area_name in month.get("assignment", {}).items()]
                            for month in history.get("months", [])
                        ]
                    )

                    log(window, f"Exported Debug Matrix: {debug_path}")

                    # Update history
                    update_history(history, assignment, people, areas)
                    save_history(history)

                    current_assignment = assignment

                log(window, "\nRota generation complete!")

            except Exception as e:
                log(window, f"ERROR: {str(e)}")

    window.close()