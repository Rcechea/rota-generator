# core/backtracking.py
"""
Backtracking solver for rota assignment.
Used when greedy assignment fails due to constraint conflicts.

The algorithm:
- Processes people in MRV-like order (fewest allowed areas first)
- Tries valid assignments area-by-area
- Backtracks if a choice leads to a dead end
- Guarantees a solution exists if constraints are satisfiable
"""

from .constraints import (
    is_assignment_valid,
    count_allowed_areas_for_person
)


def solve_with_backtracking(allowed_matrix, last_month_assignment):
    """
    Wrapper for the backtracking algorithm.
    Prepares initial data structures and calls the recursive solver.
    """
    import copy

    matrix = copy.deepcopy(allowed_matrix)

    num_areas = len(matrix)
    num_people = len(matrix[0])

    # Remove last month's assignment (same as greedy)
    for person_idx, prev_area in enumerate(last_month_assignment):
        if prev_area is not None and 0 <= prev_area < num_areas:
            matrix[prev_area][person_idx] = 0

    # Precompute priority order (fewest valid options first)
    people_with_priority = []
    for person in range(num_people):
        options = count_allowed_areas_for_person(matrix, person)
        people_with_priority.append((options, person))

    people_with_priority.sort(key=lambda x: x[0])
    ordered_people = [p for _, p in people_with_priority]

    assignment = [None] * num_people
    used_areas = set()

    if _recursive_assign(ordered_people, 0, assignment, used_areas, matrix):
        return assignment

    raise ValueError("Backtracking solver failed: no valid assignment exists.")


def _recursive_assign(people_order, index, assignment, used_areas, allowed_matrix):
    """
    Recursive DFS backtracking.
    Attempts to assign the person at `people_order[index]`.
    Returns True if a solution is found, otherwise False.
    """
    if index == len(people_order):
        # All people assigned — success!
        return True

    person = people_order[index]

    # Try every area for this person
    for area in range(len(allowed_matrix)):
        if is_assignment_valid(area, person, allowed_matrix, used_areas):

            # Tentatively assign
            assignment[person] = area
            used_areas.add(area)

            # Recurse to next person
            if _recursive_assign(people_order, index + 1, assignment, used_areas, allowed_matrix):
                return True

            # Backtrack
            used_areas.remove(area)
            assignment[person] = None

    # No valid assignment found for this person → failure
    return False