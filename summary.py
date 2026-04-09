import os, tiktoken, textwrap

enc = tiktoken.get_encoding("cl100k_base")

def summarize_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    tokens = enc.encode(content, disallowed_special=())
    truncated = enc.decode(tokens[:3000])

    summary = f"### FILE: {path}\n```\n{truncated}\n```"
    return summary


out = []

for root, dirs, files in os.walk(".", topdown=True):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "env", "venv"]]
    for file in files:
        if file.endswith((".py", ".yaml", ".yml", ".json", ".txt")):
            out.append(summarize_file(os.path.join(root, file)))

with open("project_summary.txt", "w", encoding="utf8") as f:
    f.write("\n\n".join(out))