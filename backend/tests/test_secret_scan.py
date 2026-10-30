"""Secret scan over tracked files (no third-party action).

Walks `git ls-files` from the repo root via subprocess, skips binaries by
extension and by NUL byte, and fails on token-shaped strings (Meta EAA
tokens, OpenAI sk- keys, Google OAuth secrets, refresh tokens and access
tokens, Google API keys, private-key blocks, personal non-noreply/non-example
emails). Lines containing the word FAKE or MARKER are fixtures, allowlisted
by that word only.
"""
import re
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

BINARY_EXTENSIONS = frozenset({
    ".avif", ".db", ".dll", ".eot", ".exe", ".gif", ".gz", ".ico",
    ".jpeg", ".jpg", ".mov", ".mp4", ".otf", ".pdf", ".pyc",
    ".sqlite", ".ttf", ".webm", ".webp", ".woff", ".woff2", ".zip",
})

TOKEN_PATTERNS = {
    "meta_token": re.compile("EAA" + r"[A-Za-z0-9]{20,}"),
    "openai_key": re.compile("sk-" + r"[A-Za-z0-9]{20,}"),
    "google_oauth_secret": re.compile("GOCSPX-" + r"[A-Za-z0-9_-]{10,}"),
    "google_refresh_token": re.compile("1//0" + r"[A-Za-z0-9_-]{10,}"),
    "google_access_token": re.compile("ya29" + r"\.[A-Za-z0-9_-]{10,}"),
    "google_api_key": re.compile("AIza" + r"[A-Za-z0-9_-]{35}"),
    "private_key": re.compile("-----BEGIN " + "[A-Z ]*" + "PRIVATE KEY-----"),
}

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EXAMPLE_DOMAINS = ("example.com", "example.org", "example.net")
NOREPLY_LOCALS = frozenset({"noreply", "no-reply", "donotreply", "do-not-reply"})

ALLOWLIST_WORDS = ("FAKE", "MARKER")


def _tracked_files():
    done = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [entry for entry in done.stdout.split("\0") if entry]


def _is_binary(path):
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(path, "rb") as handle:
            return b"\x00" in handle.read(8192)
    except OSError:
        return True


def _email_flagged(address):
    local, _, domain = address.partition("@")
    if domain.lower() in EXAMPLE_DOMAINS:
        return False
    if local.lower() in NOREPLY_LOCALS:
        return False
    return True


def _scan_text(text, rel):
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if any(word in line for word in ALLOWLIST_WORDS):
            continue
        for kind, pattern in TOKEN_PATTERNS.items():
            if pattern.search(line):
                findings.append(f"{rel}:{number}:{kind}")
        for address in EMAIL_PATTERN.findall(line):
            if _email_flagged(address):
                findings.append(f"{rel}:{number}:personal_email:{address}")
    return findings


def _scan_file(path, rel):
    path = Path(path)
    if _is_binary(path):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return _scan_text(text, rel)


def test_no_secrets_in_tracked_files():
    findings = []
    for rel in _tracked_files():
        findings.extend(_scan_file(REPO_ROOT / rel, rel))
    assert findings == []


def test_red_proof_fake_shaped_token_detected(tmp_path):
    token = "sk-" + "A" * 40
    target = tmp_path / "leak.txt"
    target.write_text("model_key=" + token + "\n", encoding="utf-8")
    assert _scan_file(target, "leak.txt") != []


def test_fake_word_allowlist_only(tmp_path):
    token = "sk-" + "A" * 40
    target = tmp_path / "fixture.txt"
    target.write_text("model_key=" + token + " FAKE fixture, not a leak\n", encoding="utf-8")
    assert _scan_file(target, "fixture.txt") == []


def test_personal_email_flagged_but_noreply_and_example_pass(tmp_path):
    personal = "jane.doe" + "@" + "gmail.com"
    target = tmp_path / "mail.txt"
    target.write_text("contact " + personal + "\n", encoding="utf-8")
    assert _scan_file(target, "mail.txt") != []
    target.write_text("contact " + "noreply" + "@example.com" + "\n", encoding="utf-8")
    assert _scan_file(target, "mail.txt") == []
