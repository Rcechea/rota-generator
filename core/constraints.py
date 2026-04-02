# core/constraints.py
"""
Constraint helpers for the rota solver.
Includes:
- Sickness/holiday constraints
- Validity checking
- Filtering forbidden assignments
"""

def validate_matrix_dimensions(allowed, people, areas):
    """Ensure the allowed matrix matches the number of people/areas."""
    if len(allowed) != len(areas):
        raise ValueError("Allowed-matrix row count must equal number of areas.")
    if len(allowed[0]) != len(people):
        raise ValueError("Allowed-matrix column count must equal number of people.")


def apply_sickness_constraints(allowed_matrix, people, sick_list):
    """
    If a person is sick or on holiday, they cannot be assigned to any area.
    This sets their column in the allowed matrix to all 0s.
    """
    import copy
    matrix = copy.deepcopy(allowed_matrix)

    # Map person -> index
    people_map = {p: i for i, p in enumerate(people)}

    for name in sick_list:
        if name in people_map:
            idx = people_map[name]
            # Zero out entire column
            for r in range(len(matrix)):
                matrix[r][idx] = 0

    return matrix


def is_assignment_valid(area, person, allowed_matrix, used_areas):
    """Check if assigning person -> area is valid."""
    # Area must be allowed
    if allowed_matrix[area][person] == 0:
        return False
    # Area must not already be taken
    if area in used_areas:
        return False
    return True


def get_allowed_areas_for_person(allowed_matrix, person):
    """Return list of area indices this person is allowed to take."""
    return [a for a, row in enumerate(allowed_matrix) if row[person] == 1]


def count_allowed_areas_for_person(allowed_matrix, person):
    """Return number of possible areas for person."""
    return sum(row[person] for row in allowed_matrix)