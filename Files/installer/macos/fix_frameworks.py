#!/usr/bin/env python3
"""
Repairs the macOS ".framework" folders inside an app bundle so that `codesign` accepts them.

A valid framework looks like this (the arrows are symlinks):

    Name.framework/
        Versions/A/Name                  the library
        Versions/A/Resources/Info.plist
        Versions/Current  -> A
        Name              -> Versions/Current/Name
        Resources         -> Versions/Current/Resources

Packaging tools sometimes leave out the symlinks or Info.plist (or flatten the layout), and codesign
then stops with "bundle format unrecognized, invalid, or unsuitable". This script finds every
framework, prints what is wrong (and the original layout) and repairs it.

    python installer/macos/fix_frameworks.py build/dist/AutoTyper.app
    python installer/macos/fix_frameworks.py build/dist/AutoTyper.app --check-only

Plain Python (works on any OS, so it can be tested anywhere). Exit code 0 = all frameworks valid.
"""

import argparse
import os
import plistlib
import shutil
import sys


def fw_name(path):
    return os.path.basename(path.rstrip("/"))[: -len(".framework")]


def find_frameworks(root):
    """All real (non-symlink) *.framework folders below root."""
    found = []
    for folder, dirs, _files in os.walk(root):
        keep = []
        for d in dirs:
            full = os.path.join(folder, d)
            if os.path.islink(full):
                continue
            if d.endswith(".framework"):
                found.append(full)          # do not look inside a framework for more frameworks
            else:
                keep.append(d)
        dirs[:] = keep
    return sorted(found)


def _version_dirs(fw):
    vroot = os.path.join(fw, "Versions")
    if not os.path.isdir(vroot):
        return []
    return sorted(d for d in os.listdir(vroot)
                  if d != "Current" and os.path.isdir(os.path.join(vroot, d))
                  and not os.path.islink(os.path.join(vroot, d)))


def _pick_version(fw, versions, name):
    if "A" in versions:
        return "A"
    for v in versions:
        if os.path.isfile(os.path.join(fw, "Versions", v, name)):
            return v
    return versions[0]


def problems(fw):
    """What is wrong with this framework (an empty list = valid)."""
    name = fw_name(fw)
    versions = _version_dirs(fw)
    if not versions:
        return ["no Versions/<version> folder (flat layout)"]
    v = _pick_version(fw, versions, name)
    vdir = os.path.join(fw, "Versions", v)
    out = []
    if not os.path.isfile(os.path.join(vdir, name)):
        out.append(f"missing Versions/{v}/{name}")
    if not os.path.isfile(os.path.join(vdir, "Resources", "Info.plist")):
        out.append(f"missing Versions/{v}/Resources/Info.plist")
    cur = os.path.join(fw, "Versions", "Current")
    if not (os.path.islink(cur) and os.readlink(cur) == v):
        out.append(f"Versions/Current is not a symlink to {v}")
    for link, target in ((name, f"Versions/Current/{name}"), ("Resources", "Versions/Current/Resources")):
        path = os.path.join(fw, link)
        if not (os.path.islink(path) and os.readlink(path) == target):
            out.append(f"{link} is not a symlink to {target}")
    return out


def _force_symlink(target, path, actions, label):
    if os.path.islink(path):
        if os.readlink(path) == target:
            return
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
    os.symlink(target, path)
    actions.append(f"symlink {label} -> {target}")


def _merge(src, dst):
    """Move everything from src into dst without overwriting files that already exist."""
    os.makedirs(dst, exist_ok=True)
    for folder, _dirs, files in os.walk(src):
        rel = os.path.relpath(folder, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            to = os.path.join(target_dir, f)
            if not os.path.exists(to):
                shutil.move(os.path.join(folder, f), to)


def _minimal_plist(name):
    prefix = "org.qt-project." if name.startswith("Qt") else "com.autotyper.embedded."
    return {
        "CFBundleExecutable": name, "CFBundleIdentifier": prefix + name, "CFBundleName": name,
        "CFBundlePackageType": "FMWK", "CFBundleVersion": "1", "CFBundleShortVersionString": "1.0",
        "CFBundleInfoDictionaryVersion": "6.0",
    }


def repair(fw):
    """Fix everything that can be fixed; returns the list of actions taken."""
    name = fw_name(fw)
    actions = []
    vroot = os.path.join(fw, "Versions")
    versions = _version_dirs(fw)
    if not versions:                                    # flat layout: build Versions/A from the top level
        v = "A"
        vdir = os.path.join(vroot, v)
        os.makedirs(vdir, exist_ok=True)
        actions.append("created Versions/A")
    else:
        v = _pick_version(fw, versions, name)
        vdir = os.path.join(vroot, v)

    top_exe = os.path.join(fw, name)
    if not os.path.isfile(os.path.join(vdir, name)) and os.path.isfile(top_exe) and not os.path.islink(top_exe):
        shutil.move(top_exe, os.path.join(vdir, name))
        actions.append(f"moved {name} into Versions/{v}")
    top_res = os.path.join(fw, "Resources")
    if os.path.isdir(top_res) and not os.path.islink(top_res):
        _merge(top_res, os.path.join(vdir, "Resources"))
        shutil.rmtree(top_res)
        actions.append(f"moved Resources into Versions/{v}")

    res = os.path.join(vdir, "Resources")
    os.makedirs(res, exist_ok=True)
    plist = os.path.join(res, "Info.plist")
    if not os.path.isfile(plist):
        with open(plist, "wb") as fh:
            plistlib.dump(_minimal_plist(name), fh)
        actions.append(f"created Versions/{v}/Resources/Info.plist")

    _force_symlink(v, os.path.join(vroot, "Current"), actions, "Versions/Current")
    _force_symlink(f"Versions/Current/{name}", os.path.join(fw, name), actions, name)
    _force_symlink("Versions/Current/Resources", os.path.join(fw, "Resources"), actions, "Resources")
    return actions


def listing(fw, depth=3):
    """A small tree of the framework, for the build log (shows symlinks as name -> target)."""
    lines = []
    base = len(fw.rstrip("/")) + 1
    for folder, dirs, files in os.walk(fw):
        rel = folder[base:] if len(folder) >= base else ""
        if rel.count("/") >= depth:
            dirs[:] = []
        for entry in sorted(dirs + files):
            full = os.path.join(folder, entry)
            shown = (rel + "/" if rel else "") + entry
            if os.path.islink(full):
                lines.append(f"    {shown} -> {os.readlink(full)}")
            elif os.path.isdir(full):
                lines.append(f"    {shown}/")
            else:
                lines.append(f"    {shown}  ({os.path.getsize(full)} bytes)")
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(folder, d))]
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.app):
        print(f"Not a folder: {args.app}", file=sys.stderr)
        return 2

    frameworks = find_frameworks(args.app)
    broken = repaired = 0
    for fw in frameworks:
        before = problems(fw)
        if not before:
            continue
        broken += 1
        rel = os.path.relpath(fw, args.app)
        print(f"- {rel}")
        for p in before:
            print(f"    problem: {p}")
        print("    layout found:")
        print("\n".join(listing(fw)) or "    (empty)")
        if args.check_only:
            continue
        for action in repair(fw):
            print(f"    fixed: {action}")
        after = problems(fw)
        if after:
            for p in after:
                print(f"    STILL WRONG: {p}")
        else:
            repaired += 1
    still = broken - repaired if not args.check_only else broken
    print(f"Frameworks checked: {len(frameworks)}, needing repair: {broken}, repaired: {repaired if not args.check_only else 0}, "
          f"still invalid: {still}")
    return 0 if still == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
