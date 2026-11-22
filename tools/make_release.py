"""Builds the downloadable release zip: dist/MagicKeyboardHelper-v<version>.zip

The zip holds a ready-to-run "MagicKeyboardHelper" folder: the app, the Fn / Lock
patch, the icons, the README and the unchanged AutoHotkey64.exe runtime (with its
GPL license), so users do not need to install AutoHotkey.

The AutoHotkey zip is downloaded from autohotkey.com and checked against a pinned
SHA-256 (the same hash is published at autohotkey.com and on the AutoHotkey GitHub
release). Python 3.8+ standard library only.

Usage:
    python tools/make_release.py                  # build
    python tools/make_release.py --check-tag v3.3 # fail if the app version is not 3.3
    python tools/make_release.py --ahk-zip FILE   # use a local AutoHotkey zip
"""
import argparse
import hashlib
import io
import os
import re
import sys
import urllib.request
import zipfile

AHK_VERSION = "2.0.21"
AHK_URL = f"https://www.autohotkey.com/download/2.0/AutoHotkey_{AHK_VERSION}.zip"
AHK_SHA256 = "7386f45be928f0825ffbe78811187636d72efcbd264e2fd406e7e045d681a626"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
FOLDER = "MagicKeyboardHelper"

# Files of the app that go into the zip (make_icon.py and the tools are for developers)
APP_FILES = [
    "MagicKeyboardHelper.bat",
    "magic_keyboard_media.ahk",
    "fn_lock_patch.bat",
    "fn_lock_patch.ps1",
    "magic_keyboard.ico",
    "magic_keyboard_charging.ico",
    "magic_keyboard_low.ico",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
]
TEXT_EXT = {".bat", ".ahk", ".ps1", ".md", ".txt", ""}

THIRD_PARTY = f"""Third-party software in this package
=====================================

AutoHotkey64.exe
    AutoHotkey v{AHK_VERSION}, unchanged, from {AHK_URL}
    SHA-256 of the downloaded zip: {AHK_SHA256}
    License: GNU General Public License v2, see AutoHotkey-LICENSE.txt
    Source code: https://github.com/AutoHotkey/AutoHotkey/tree/v{AHK_VERSION}
"""


def app_version():
    src = open(os.path.join(ROOT, "magic_keyboard_media.ahk"), encoding="utf-8").read()
    m = re.search(r'^global APP_VERSION := "([^"]+)"', src, re.M)
    if not m:
        sys.exit("APP_VERSION not found in magic_keyboard_media.ahk")
    return m.group(1)


def release_notes(version):
    """The CHANGELOG.md section of this version."""
    text = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(rf"^## v?{re.escape(version)}\b.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        sys.exit(f"No '## {version}' section in CHANGELOG.md")
    return m.group(1).strip() + "\n"


def get_ahk_zip(path):
    if path:
        data = open(path, "rb").read()
    else:
        cache = os.path.join(DIST, f"AutoHotkey_{AHK_VERSION}.zip")
        if os.path.exists(cache):
            data = open(cache, "rb").read()
        else:
            print("Downloading", AHK_URL)
            req = urllib.request.Request(AHK_URL, headers={"User-Agent": "release-builder"})
            data = urllib.request.urlopen(req, timeout=120).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != AHK_SHA256:
        sys.exit(f"AutoHotkey zip SHA-256 mismatch: {digest}")
    if not path:
        os.makedirs(DIST, exist_ok=True)
        with open(os.path.join(DIST, f"AutoHotkey_{AHK_VERSION}.zip"), "wb") as f:
            f.write(data)
    return zipfile.ZipFile(io.BytesIO(data))


def crlf(data):
    """Windows line endings for text files (keeps a UTF-8 BOM)."""
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-tag", help="git tag, e.g. v3.3: must match APP_VERSION")
    ap.add_argument("--ahk-zip", help="local AutoHotkey zip instead of downloading")
    args = ap.parse_args()

    version = app_version()
    if args.check_tag and args.check_tag.lstrip("v") != version:
        sys.exit(f"Tag {args.check_tag} does not match APP_VERSION {version}")

    ahk = get_ahk_zip(args.ahk_zip)
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, f"MagicKeyboardHelper-v{version}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in APP_FILES:
            data = open(os.path.join(ROOT, name), "rb").read()
            if os.path.splitext(name)[1].lower() in TEXT_EXT:
                data = crlf(data)
            z.writestr(f"{FOLDER}/{name}", data)
        z.writestr(f"{FOLDER}/AutoHotkey64.exe", ahk.read("AutoHotkey64.exe"))
        z.writestr(f"{FOLDER}/AutoHotkey-LICENSE.txt", crlf(ahk.read("license.txt")))
        z.writestr(f"{FOLDER}/THIRD-PARTY.txt", crlf(THIRD_PARTY.encode("utf-8")))

    with open(os.path.join(DIST, "RELEASE_NOTES.md"), "w", encoding="utf-8") as f:
        f.write(release_notes(version))
    print(f"Built {out} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
