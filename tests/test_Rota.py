import pytest
import numpy as np

from core.constraints import apply_sickness_constraints, is_assignment_valid
from core.weights import build_weighted_cost_matrix, LARGE_PENALTY
from core.greedy import greedy_assign
from core.optimal import solve_optimal
from core.history import update_history


# ---------------------------------------------------------
# ✅ TEST 1 — Sickness removes allowed areas
# ---------------------------------------------------------
def test_sickness_constraints():
    allowed = [
        [1, 1],  # area 0
        [1, 1],  # area 1
    ]
    people = ["A", "B"]
    sick = ["A"]

    new_matrix = apply_sickness_constraints(allowed, people, sick)

    # A = person index 0 → all zeros
    assert new_matrix[0][0] == 0
    assert new_matrix[1][0] == 0

    # B should remain unchanged
    assert new_matrix[0][1] == 1
    assert new_matrix[1][1] == 1


# ---------------------------------------------------------
# ✅ TEST 2 — Weighted matrix applies LARGE_PENALTY for invalid cells
# ---------------------------------------------------------
def test_weighted_cost_matrix_penalties():
    allowed = [
        [1, 0],  # Person 1 banned from area 1
        [1, 1],
    ]
    people = ["A", "B"]
    areas = ["X", "Y"]

    # Fake minimal history (all zeros)
    history = {"months": []}

    cost = build_weighted_cost_matrix(allowed, people, areas, history)

    assert cost[0][1] == LARGE_PENALTY  # forbidden cell
    assert cost[1][1] < LARGE_PENALTY   # allowed cell


# ---------------------------------------------------------
# ✅ TEST 3 — Greedy solver returns a valid assignment
# ---------------------------------------------------------
def test_greedy_assign_validity():
    people = ["A", "B"]
    areas = ["X", "Y"]

    allowed = [
        [1, 1],  # area X
        [1, 1],  # area Y
    ]

    last_month = [-1, -1]  # no constraints
    cost_matrix = np.array([
        [1, 1],
        [1, 1],
    ])

    result = greedy_assign(allowed, last_month, people, areas, cost_matrix)

    # Assignment must have exactly one area per person
    assert len(result) == len(people)

    # No duplicate areas
    assert len(set(result)) == len(people)


# ---------------------------------------------------------
# ✅ TEST 4 — Optimal solver respects forbidden assignments
# ---------------------------------------------------------
def test_optimal_solver_respects_forbidden():
    # Person A cannot go to area 0
    cost_matrix = np.array([
        [LARGE_PENALTY, 1],  # area 0
        [1, 1],              # area 1
    ])

    assignment = solve_optimal(cost_matrix)

    # Person 0 (A) must NOT be assigned area 0
    assert assignment[0] != 0


# ---------------------------------------------------------
# ✅ TEST 5 — History update produces correct output mapping
# ---------------------------------------------------------
def test_history_update():
    history = {"months": []}
    people = ["A", "B"]
    areas = ["X", "Y"]

    assignment = [0, 1]  # A->X, B->Y

    update_history(history, assignment, people, areas)

    assert len(history["months"]) == 1
    record = history["months"][0]["assignment"]

    assert record["A"] == "X"
    assert record["B"] == "Y"