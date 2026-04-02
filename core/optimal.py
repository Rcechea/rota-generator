# core/optimal.py
"""
Optimal assignment solver using the Hungarian algorithm (linear_sum_assignment).

This version is SAFE for use as the primary solver:
- Validates that no forbidden assignments are returned
- Enforces LARGE_PENALTY for illegal cells
- Guarantees assignment[person] = area_index
"""

import numpy as np
from scipy.optimize import linear_sum_assignment

LARGE_PENALTY = 10_000_000   # Forbidden assignments must use this


def solve_optimal(cost_matrix):
    """
    Solve assignment using the Hungarian algorithm.

    cost_matrix shape must be:
        rows   = areas
        columns = people

    Returns:
        assignment: list where index = person, value = assigned area
    """

    C = np.array(cost_matrix)

    # If cost matrix is not square: pad it
    rows, cols = C.shape
    if rows != cols:
        max_dim = max(rows, cols)
        padded = np.full((max_dim, max_dim), LARGE_PENALTY, dtype=float)
        padded[:rows, :cols] = C
        C_working = padded
    else:
        C_working = C

    # Run Hungarian solver
    row_ind, col_ind = linear_sum_assignment(C_working)

    # Build final assignment ONLY for valid people/areas
    assignment = [None] * cols  # one entry per person

    for area_idx, person_idx in zip(row_ind, col_ind):

        # Ignore padded dummy rows/columns
        if area_idx >= rows or person_idx >= cols:
            continue

        # Validate: LARGE_PENALTY means forbidden
        if C[area_idx][person_idx] >= LARGE_PENALTY:
            raise ValueError(
                f"Optimal solver produced forbidden assignment: "
                f"area={area_idx}, person={person_idx}"
            )

        assignment[person_idx] = area_idx

    # Final validation: no unassigned persons
    if any(a is None for a in assignment):
        raise ValueError("Optimal solver failed to assign all people.")

    return assignment
