import pandas as pd

# Same recency colors as before
RECENCY_COLORS = [
    "#A7D8FF", "#73E0C1", "#7CF37A", "#C6F56F",
    "#E4F55B", "#FFD753", "#FFB870", "#FF8A8A",
    "#FF5757", "#AC6BFF", "#9457D6", "#6133A1"
]

def build_debug_dataframe(people, areas, allowed_matrix, assignment, history_assignments):
    
    df = pd.DataFrame(index=areas, columns=people, dtype=str)

    # Reverse history, index 0 = last month
    rev_hist = list(reversed(history_assignments))

    for a_idx, area in enumerate(areas):
        for p_idx, person in enumerate(people):

            # Forbidden
            if allowed_matrix[a_idx][p_idx] == 0:
                df.loc[area, person] = "FORBIDDEN"
                continue

            # Check recency
            past_age = None
            for i, month in enumerate(rev_hist):
                if p_idx < len(month) and month[p_idx] == a_idx:
                    past_age = i + 1
                    break

            # This month
            if assignment[p_idx] == a_idx:
                if past_age is None:
                    df.loc[area, person] = "✓"
                else:
                    df.loc[area, person] = f"✓ ({past_age})"
                continue

            # Past months
            if past_age is not None:
                df.loc[area, person] = str(past_age)
                continue

            # Allowed, unused
            df.loc[area, person] = ""

    # Now apply colors using Styler
    def colorize(val):
        if val == "FORBIDDEN":
            return "background-color: black; color: white;"
        if val.startswith("✓"):
            # current month (yellow)
            return "background-color: yellow;"
        if val.isdigit():
            age = int(val)
            idx = min(age - 1, len(RECENCY_COLORS) - 1)
            return f"background-color: {RECENCY_COLORS[idx]};"
        return ""  # unused

    styled = df.style.map(colorize)
    return df, styled