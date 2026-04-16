"""Orchestrator installer — set up multi-agent workflow prompts for your AI coding platform.

Usage:
    python install.py                              # interactive mode
    python install.py /path/to/project -p opencode  # project-local
    python install.py -g -p opencode                # global (user-level config)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration_layer.installer import (  # noqa: E402
    PLATFORM_DISPLAY_NAMES,
    PLATFORM_GLOBAL_ROOTS,
    SUPPORTED_PLATFORMS,
    install_platforms,
)


def _header() -> None:
    print()
    print("Orchestrator Installer")
    print()


def _prompt_choice(prompt: str, options: list[str]) -> int:
    print(prompt)
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    print()
    while True:
        raw = input("Choose: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        print(f"  Enter a number between 1 and {len(options)}.")


def _prompt_path() -> Path:
    while True:
        raw = input("\nProject path: ").strip()
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            return path
        print(f"  Directory not found: {path}")


def _prompt_platforms(global_mode: bool) -> list[str]:
    available = [
        p for p in SUPPORTED_PLATFORMS
        if not global_mode or PLATFORM_GLOBAL_ROOTS.get(p) is not None
    ]
    labels = [PLATFORM_DISPLAY_NAMES[p] for p in available]
    all_idx = len(labels) + 1

    print("\nWhich platform(s)?")
    for i, label in enumerate(labels, 1):
        print(f"  [{i}] {label}")
    print(f"  [{all_idx}] All")
    print()
    print("  Enter one number, or multiple separated by commas (e.g. 1,3).")

    while True:
        raw = input("Choose: ").strip()
        indices: list[int] = []
        ok = True
        for part in raw.split(","):
            part = part.strip()
            if not part.isdigit():
                ok = False
                break
            idx = int(part)
            if idx == all_idx:
                return list(available)
            if 1 <= idx <= len(labels):
                indices.append(idx)
            else:
                ok = False
                break
        if ok and indices:
            return [available[i - 1] for i in indices]
        print(f"  Enter valid numbers between 1 and {all_idx}.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Orchestrator multi-agent workflow prompts.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Target directory. If omitted, the installer runs interactively.",
    )
    parser.add_argument(
        "--platform", "-p",
        action="append",
        choices=[*SUPPORTED_PLATFORMS, "all"],
        help="Platform to install. Repeat for multiple. If omitted, the installer asks.",
    )
    parser.add_argument(
        "--global", "-g",
        action="store_true",
        dest="global_install",
        help="Install to user-level config instead of a project directory.",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    force = args.force
    global_install = args.global_install
    interactive = not global_install and (args.target is None or args.platform is None)

    if interactive:
        _header()

    if global_install:
        target_root = None
        global_mode = True
    elif args.target is None:
        cwd_display = str(Path.cwd())
        choice = _prompt_choice(
            "Where to install?",
            [
                f"Current directory ({cwd_display})",
                "Specify a project path",
                "Global install (user-level config)",
            ],
        )
        if choice == 1:
            target_root = Path.cwd()
            global_mode = False
        elif choice == 2:
            target_root = _prompt_path()
            global_mode = False
        else:
            target_root = None
            global_mode = True
    else:
        target_root = Path(args.target).expanduser().resolve()
        global_mode = False

    if args.platform is None:
        platforms = _prompt_platforms(global_mode)
    else:
        platforms = args.platform
        if "all" in platforms:
            platforms = list(SUPPORTED_PLATFORMS)

    if global_mode:
        for platform in platforms:
            global_root = PLATFORM_GLOBAL_ROOTS.get(platform)
            if global_root is None:
                print(f"\n  Global install not available for {PLATFORM_DISPLAY_NAMES[platform]}. Skipping.")
                continue
            print(f"\nInstalling {PLATFORM_DISPLAY_NAMES[platform]} to {global_root} ...")
            installed = install_platforms(global_root, platforms=[platform], force=force, global_mode=True)
            print(f"  {len(installed)} files installed.")
        print("\nDone.")
    else:
        assert target_root is not None
        target_root.mkdir(parents=True, exist_ok=True)
        installed = install_platforms(target_root, platforms=platforms, force=force)
        platform_labels = ", ".join(PLATFORM_DISPLAY_NAMES.get(p, p) for p in platforms)
        print(f"\nInstalled {len(installed)} files to {target_root}")
        print(f"Platforms: {platform_labels}")
        print("\nNext: open the project in your AI coding tool and check the quickstart file.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
