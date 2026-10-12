"""
Size report for a built AutoTyper bundle (dist folder or .app) - plain Python, any OS.

    python installer/size_report.py build/dist/AutoTyper                  # biggest files + totals
    python installer/size_report.py build/dist/AutoTyper --save after.json
    python installer/size_report.py --compare before.json after.json      # before / after per category

To measure "before": build once with AUTOTYPER_NO_PRUNE=1, save the report, build again normally
and compare. (The installer's own size is printed by the build scripts.)
"""

import argparse
import json
import os
import sys

BUDGET_MB = 25.0


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


def scan(root):
    """[(size in bytes, relative path)] of all real files (symlinks are not followed or counted)."""
    entries = []
    for folder, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(folder, name)
            if os.path.islink(path):
                continue
            entries.append((os.path.getsize(path), os.path.relpath(path, root).replace(os.sep, "/")))
    return entries


def category(rel):
    p = rel.lower()
    base = p.rsplit("/", 1)[-1]
    stem = base.split(".")[0]
    stem = stem[3:] if stem.startswith("lib") else stem
    is_binary = base.endswith((".dll", ".so", ".dylib", ".pyd")) or ".framework/" in p
    if "/plugins/" in p:
        return "Qt plugins"
    if base.endswith(".qm") or "/translations/" in p:
        return "Qt translations"
    if base in ("opengl32sw.dll", "d3dcompiler_47.dll") or (is_binary and stem.startswith("qt") and len(stem) > 2):
        return "Qt libraries"
    if base.startswith(("python", "libpython", "base_library")) or "/lib-dynload/" in p:
        return "Python runtime"
    if "pyside6" in p or "shiboken" in p:
        return "PySide6 / shiboken"
    if is_binary:
        return "Other libraries"
    return "App and data"


def summarize(entries):
    total = sum(s for s, _ in entries)
    cats = {}
    for size, rel in entries:
        cats[category(rel)] = cats.get(category(rel), 0) + size
    return total, cats


def report(root, top=15):
    entries = scan(root)
    total, cats = summarize(entries)
    lines = [f"Bundle: {root}", f"Total size on disk: {human(total)} in {len(entries)} files", "",
             "By category:"]
    for name, size in sorted(cats.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {human(size):>10}  {name}")
    lines += ["", f"{top} largest files:"]
    for size, rel in sorted(entries, reverse=True)[:top]:
        lines.append(f"  {human(size):>10}  {rel}")
    return "\n".join(lines), {"total": total, "files": len(entries), "categories": cats}


def compare(before, after):
    lines = [f"Total: {human(before['total'])} -> {human(after['total'])}  "
             f"({'-' if after['total'] <= before['total'] else '+'}{human(abs(after['total'] - before['total']))})", ""]
    names = sorted(set(before["categories"]) | set(after["categories"]),
                   key=lambda n: -(before["categories"].get(n, 0)))
    for name in names:
        b, a = before["categories"].get(name, 0), after["categories"].get(name, 0)
        lines.append(f"  {name:<22} {human(b):>10} -> {human(a):>10}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--save")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = ap.parse_args(argv)
    if args.compare:
        with open(args.compare[0], encoding="utf-8") as a, open(args.compare[1], encoding="utf-8") as b:
            print(compare(json.load(a), json.load(b)))
        return 0
    if not args.path or not os.path.isdir(args.path):
        print("Give the folder of the built app (for example build/dist/AutoTyper).", file=sys.stderr)
        return 2
    text, data = report(args.path, args.top)
    print(text)
    if args.save:
        with open(args.save, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
