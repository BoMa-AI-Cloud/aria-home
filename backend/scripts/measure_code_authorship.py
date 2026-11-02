"""Who wrote the code in a tree: git blame per line, classified by the commit that wrote it.

Usage: python authorship.py <ref> [base-sha]
Claude = commits after the base that are not Muse-run commits, plus any earlier commit named in CLAUDE_EARLIER.
Everything else = Muse models and Meta AI web chat, including small operator adjustments recorded in the operator log,
which blame cannot separate inside a squash commit.
"""
import subprocess
import sys
from collections import Counter

REPO = "C:/aria-home"
REF = sys.argv[1] if len(sys.argv) > 1 else "main"
BASE = sys.argv[2] if len(sys.argv) > 2 else "8a94f53"


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, encoding="utf8", errors="replace").stdout


MUSE_MARK = ("Written by Muse",)
later = git("rev-list", f"{BASE}..{REF}").split()
claude = set()
for sha in later:
    msg = git("log", "-1", "--format=%B", sha)
    if git("rev-list", "--parents", "-n1", sha).count(" ") > 1:
        continue
    if any(m in msg for m in MUSE_MARK):
        continue
    claude.add(sha)
GROUPS = {
    "application code (backend/aria_home, frontend/src)": lambda f: (f.startswith("backend/aria_home/") and f.endswith(".py")) or (f.startswith("frontend/src/") and f.endswith((".ts", ".tsx", ".css"))),
    "tests (backend/tests, frontend/e2e)": lambda f: (f.startswith("backend/tests/") and f.endswith(".py")) or (f.startswith("frontend/e2e/") and f.endswith(".ts")),
    "scripts (backend/scripts .py)": lambda f: f.startswith("backend/scripts/") and f.endswith(".py"),
}
files = git("ls-tree", "-r", "--name-only", REF).splitlines()
print(f"ref {REF} {git('rev-parse', '--short', REF).strip()}; Claude commits after {BASE}: {len(claude)}; later commits total {len(later)}")
total = Counter()
for name, match in GROUPS.items():
    c = Counter()
    for f in files:
        if not match(f):
            continue
        for line in git("blame", "--line-porcelain", REF, "--", f).splitlines():
            if len(line) >= 40 and line.split(" ")[0].isalnum() and len(line.split(" ")[0]) == 40 and len(line.split(" ")) >= 3:
                c["claude" if line.split(" ")[0] in claude else "muse"] += 1
    n = sum(c.values())
    total.update(c)
    print(f"{name}: {n} lines; Muse and Meta AI {c['muse']} ({100 * c['muse'] / max(n, 1):.1f}%), Claude {c['claude']} ({100 * c['claude'] / max(n, 1):.1f}%)")
n = sum(total.values())
print(f"all code: {n} lines; Muse and Meta AI {100 * total['muse'] / n:.1f}%, Claude {100 * total['claude'] / n:.1f}%")
