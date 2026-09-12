"""Reject unexpected assets and private configuration in the committed tree."""
from pathlib import PurePosixPath
import subprocess

IMAGES = {
    "publication/images/book-cover.jpg", "publication/images/exs_zones.png",
    "publication/images/kick_comparison.png", "publication/images/nam_before_after.png",
    "publication/images/stems_null_test.png", "publication/images/stems_stack.png",
}
TEXT = {".py", ".md", ".txt", ".yml", ".yaml", ".css"}
SPECIAL = {"LICENSE", ".gitignore"}
PRIVATE = {".env", ".aws", ".ssh", ".claude", ".codex", ".vscode", ".idea",
           "samples", "soundfonts", "amps", "irs", "sources", "releases", "auditions"}
errors = []
entries = subprocess.check_output(["git", "ls-tree", "-rz", "HEAD"]).split(b"\0")
count = 0
for entry in entries:
    if not entry:
        continue
    metadata, raw_path = entry.split(b"\t", 1)
    mode, kind, oid = metadata.decode().split()
    name = raw_path.decode()
    path = PurePosixPath(name)
    count += 1
    private = any(p.lower() in PRIVATE or p.lower().startswith(".env.") for p in path.parts)
    permitted = name in IMAGES or name in SPECIAL or path.suffix in TEXT
    if private or not permitted or kind != "blob" or mode not in {"100644", "100755"}:
        errors.append(name)
        continue
    data = subprocess.check_output(["git", "cat-file", "blob", oid])
    if name in IMAGES:
        signature = b"\x89PNG\r\n\x1a\n" if name.endswith(".png") else b"\xff\xd8\xff"
        if not data.startswith(signature):
            errors.append(name)
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(name)
        if b"\0" in data or data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            errors.append(name)
if errors:
    raise SystemExit("Unexpected public files (review locally): " + ", ".join(sorted(set(errors))))
print(f"Public inventory passed: {count} committed files; no unexpected binaries or private paths.")
