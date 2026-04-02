# core/greedy.py
"""
Dynamic Weighted MRV Greedy Solver.

Features:
- Dynamic MRV: recalculates allowed areas after EACH assignment
- Weighted MRV: picks next person based on fewest AND worst weighted options
- Weighted Area Ordering: selects best available area by lowest weight
- Hard constraints remain absolute (forbidden, sickness, last-month, used areas)
- Fully verbose logs with person and area names
"""

from .constraints import is_assignment_valid


def greedy_assign(
    allowed_matrix,
    last_month_assignment,
    people,
    areas,
    cost_matrix,
    debug_log=None
):
    import copy

    # Deep copy so we don't mutate original
    matrix = copy.deepcopy(allowed_matrix)

    num_areas = len(matrix)
    num_people = len(matrix[0])

    def dbg(msg):
        if debug_log:
            debug_log(msg)

    dbg("=== DYNAMIC WEIGHTED GREEDY STARTED ===")

    # ------------------------------------------------------------
    # STEP 1 — Last-month hard exclusion
    # ------------------------------------------------------------
    dbg("\n=== STEP 1: Removing last month's assignments ===")
    for person_idx, prev_area in enumerate(last_month_assignment):
        if prev_area is not None and 0 <= prev_area < num_areas:
            matrix[prev_area][person_idx] = 0
            dbg(f"{people[person_idx]} cannot repeat '{areas[prev_area]}'")

    # Prepare assignment tracking
    assignment = [None] * num_people
    used_areas = set()
    unassigned = set(range(num_people))

    # ------------------------------------------------------------
    # MAIN LOOP — Dynamic & Weighted MRV
    # ------------------------------------------------------------
    while unassigned:

        dbg("\n=== Recalculating Weighted MRV ===")

        mrv_list = []

        for person in unassigned:
            # Identify valid remaining areas
            allowed_areas = [
                a for a in range(num_areas)
                if matrix[a][person] == 1 and a not in used_areas
            ]

            allowed_count = len(allowed_areas)

            # Weighted MRV: sum of weights for available areas (lower = better)
            if allowed_areas:
                weight_sum = sum(cost_matrix[a][person] for a in allowed_areas)
            else:
                weight_sum = 999999999  # Makes this person selected when stuck

            mrv_list.append((allowed_count, weight_sum, person))

            dbg(
                f"{people[person]} → {allowed_count} areas, "
                f"total_weight={weight_sum}"
            )

        # Sort by:
        # 1. Fewest allowed areas (MRV)
        # 2. Worst weighted options
        mrv_list.sort(key=lambda x: (x[0], x[1]))

        allowed_count, weight_sum, person = mrv_list[0]

        if allowed_count == 0:
            dbg(f"❌ DEAD-END: {people[person]} has no valid areas left")
            raise ValueError(f"Dynamic Weighted Greedy failed for {people[person]}")

        dbg(
            f"\n→ Next person to assign: {people[person]} "
            f"(allowed={allowed_count}, weighted_sum={weight_sum})"
        )

        # ------------------------------------------------------------
        # Weighted Area Ordering
        # ------------------------------------------------------------
        weighted_areas = sorted(
            range(num_areas),
            key=lambda a: cost_matrix[a][person]
        )

        # Try areas in weighted order
        assigned_flag = False

        for area in weighted_areas:

            can_assign = matrix[area][person] == 1
            already_used = area in used_areas

            dbg(
                f"Checking '{areas[area]}' "
                f"(allowed={can_assign}, used={already_used}, "
                f"weight={cost_matrix[area][person]})"
            )

            if can_assign and not already_used:
                dbg(f"✔ Assign {people[person]} → '{areas[area]}' "
                    f"(weight {cost_matrix[area][person]})")
                assignment[person] = area
                used_areas.add(area)
                unassigned.remove(person)
                assigned_flag = True
                break

        if not assigned_flag:
            dbg(f"❌ FAILED: No valid weighted area for {people[person]}")
            raise ValueError(f"Dynamic Weighted Greedy failed for {people[person]}")

    dbg("\n✔ DYNAMIC WEIGHTED GREEDY SUCCESSFUL")
    return assignment