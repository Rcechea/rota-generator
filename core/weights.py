# core/weights.py
"""
Build a weighted cost matrix for the Hungarian optimal solver.

Costs:
- Forbidden areas (LARGE_PENALTY)
- Sickness (LARGE_PENALTY)
- Recent assignments → strong penalty
- Older assignments → weaker penalty
"""

LARGE_PENALTY = 10_000_000  # Forbidden or impossible
MEDIUM_PENALTY = 10_000     # Optional last-month boost (unused now)

# Recency-based penalty schedule
RECENCY_WEIGHTS = [
    10_000,   # last month
    8_000,    # 2 months ago
    6_000,    # 3 months ago
    4_000,    # 4 months ago
    2_000,    # 5 months ago
    1_000,    # 6+ months ago
]


def build_weighted_cost_matrix(allowed_matrix, people, areas, history):
    """
    Construct a full weighted cost matrix:
        cost[area][person]

    Recency-based penalties discourage repeating areas too soon.
    Forbidden/sickness entries = LARGE_PENALTY.
    """
    num_areas = len(allowed_matrix)
    num_people = len(allowed_matrix[0])
    cost = [[0 for _ in range(num_people)] for _ in range(num_areas)]

    # Build person/area indices
    person_index = {p: i for i, p in enumerate(people)}
    area_index = {a: i for i, a in enumerate(areas)}

    # ------------------------------------------------------------------------
    # APPLY RECENCY-WEIGHTED FAIRNESS PENALTIES
    # ------------------------------------------------------------------------
    if history and "months" in history:
        months_history = history["months"]

        # Reverse: newest first
        for months_back, month_entry in enumerate(reversed(months_history)):
            # Beyond schedule → use last value
            weight = RECENCY_WEIGHTS[min(months_back, len(RECENCY_WEIGHTS) - 1)]

            assignment = month_entry.get("assignment", {})
            for person_name, area_name in assignment.items():

                # Clean BOM
                area_name = area_name.replace("\ufeff", "").replace("ï»¿", "")

                if person_name in person_index and area_name in area_index:
                    p = person_index[person_name]
                    a = area_index[area_name]

                    # Add recency penalty
                    cost[a][p] += weight

    # ------------------------------------------------------------------------
    # APPLY FORBIDDEN/SICKNESS PENALTIES
    # ------------------------------------------------------------------------
    for a in range(num_areas):
        for p in range(num_people):
            if allowed_matrix[a][p] == 0:
                cost[a][p] = LARGE_PENALTY

    return cost