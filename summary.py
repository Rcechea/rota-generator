import os
import tiktoken

# ----------------------------------------------------
# TOKENIZER
# ----------------------------------------------------
enc = tiktoken.get_encoding("cl100k_base")

# ----------------------------------------------------
# DIRECTORIES TO INCLUDE
# Only files inside these directories are summarized
# ----------------------------------------------------
WHITELIST_DIRS = {
    ".",            # root
    "core",
    "tests",
}

# ----------------------------------------------------
# DIRECTORIES TO EXCLUDE ENTIRELY
# ----------------------------------------------------
BLACKLIST_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "node_modules",
    "data",     # avoid huge output
}

# ----------------------------------------------------
# FILE EXTENSIONS TO INCLUDE
# ----------------------------------------------------
EXTENSIONS = {
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
}

# ----------------------------------------------------
# SKIP TXT FILES LARGER THAN THIS (bytes)
# ----------------------------------------------------
MAX_TXT_SIZE = 100_000  # 100 KB


# ----------------------------------------------------
# UTILS
# ----------------------------------------------------
def is_binary_string(data: str) -> bool:
    """Heuristic check to detect if a file is binary despite extension."""
    # If >30% chars are non-text, treat as binary
    if not data:
        return False
    nontext = sum(c < " " and c not in "\t\r\n" for c in data)
    return (nontext / len(data)) > 0.30


def summarize_file(path):
    """Return a formatted summary block for a single file."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return f"### FILE: {path}\n```\n[ERROR: Could not read file]\n```"

    # Skip binary‑looking files
    if is_binary_string(content):
        return f"### FILE: {path}\n```\n[Skipped: binary content]\n```"

    # Token limit
    tokens = enc.encode(content, disallowed_special=())
    truncated = enc.decode(tokens[:3000])

    size = os.path.getsize(path)
    ext = os.path.splitext(path)[1]
    lang = ext.replace(".", "") or ""

    return (
        f"### FILE: {path} ({size} bytes)\n"
        f"```{lang}\n{truncated}\n```\n"
    )


# ----------------------------------------------------
# DIRECTORY FILTERS
# ----------------------------------------------------
def should_include_dir(dirpath):
    clean = dirpath.lstrip("./")

    # Whitelist exact matches
    if clean in WHITELIST_DIRS:
        return True

    # Exclude blacklisted dirs
    for bad in BLACKLIST_DIRS:
        if f"{os.sep}{bad}{os.sep}" in dirpath + os.sep:
            return False

    return True


# ----------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------
def main():
    output = []
    included_files = 0
    total_size = 0

    for root, dirs, files in os.walk(".", topdown=True):

        # Filter subdirectories
        dirs[:] = [d for d in dirs if should_include_dir(os.path.join(root, d))]

        # Skip full subtree if root itself isn't in whitelist
        if not should_include_dir(root):
            continue

        for file in files:
            path = os.path.join(root, file)
            ext = os.path.splitext(file)[1]

            if ext not in EXTENSIONS:
                continue

            # Skip large text files
            if ext == ".txt" and os.path.getsize(path) > MAX_TXT_SIZE:
                continue

            summary = summarize_file(path)
            output.append(summary)

            included_files += 1
            total_size += os.path.getsize(path)

    # Sort alphabetically for deterministic output
    output.sort()

    # Append summary footer
    footer = (
        "\n---\n"
        f"**Total files included:** {included_files}\n\n"
        f"**Total summarized size:** {total_size} bytes\n"
    )

    with open("project_summary.txt", "w", encoding="utf8") as f:
        f.write("\n".join(output) + footer)

    print("✅ project_summary.txt generated!")


if __name__ == "__main__":
    main()