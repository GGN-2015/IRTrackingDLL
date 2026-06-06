#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


def existing_file(path):
    if not path:
        return None

    candidate = Path(path)
    return candidate if candidate.is_file() else None


def find_vswhere():
    found = shutil.which("vswhere")
    if found:
        return Path(found)

    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def find_msbuild_with_vswhere(vswhere):
    commands = [
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.Component.MSBuild",
            "-find",
            r"MSBuild\Current\Bin\amd64\MSBuild.exe",
        ],
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.Component.MSBuild",
            "-find",
            r"MSBuild\Current\Bin\MSBuild.exe",
        ],
    ]

    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            continue

        for line in result.stdout.splitlines():
            candidate = existing_file(line.strip())
            if candidate:
                return candidate

    return None


def find_msbuild():
    msbuild_from_env = existing_file(os.environ.get("MSBUILD_EXE"))
    if msbuild_from_env:
        return msbuild_from_env

    msbuild_from_path = shutil.which("msbuild")
    if msbuild_from_path:
        return Path(msbuild_from_path)

    vswhere = find_vswhere()
    if vswhere:
        msbuild = find_msbuild_with_vswhere(vswhere)
        if msbuild:
            return msbuild

    return None


def run(command):
    print(flush=True)
    print(" ".join(f'"{part}"' if " " in str(part) else str(part) for part in command), flush=True)
    return subprocess.run(command, cwd=ROOT_DIR).returncode


def parse_args():
    parser = argparse.ArgumentParser(description="Restore and build the HL2DinoPlugin solution.")
    parser.add_argument("--configuration", "-c", default="Release", help="MSBuild configuration. Default: Release")
    parser.add_argument("--platform", "-p", default="ARM64", help="MSBuild platform. Default: ARM64")
    parser.add_argument("--solution", "-s", default="HL2DinoPlugin.sln", help="Solution file. Default: HL2DinoPlugin.sln")
    parser.add_argument("--no-restore", action="store_true", help="Skip NuGet package restore.")
    return parser.parse_args()


def main():
    args = parse_args()

    solution = ROOT_DIR / args.solution
    if not solution.is_file():
        print(f"Solution file not found: {solution}", file=sys.stderr)
        return 1

    msbuild = find_msbuild()
    if not msbuild:
        print(
            "Unable to find MSBuild.exe.\n"
            "Install Visual Studio with C++/UWP build tools, or set MSBUILD_EXE to the full MSBuild.exe path.",
            file=sys.stderr,
        )
        return 1

    print(f"Using MSBuild: {msbuild}", flush=True)

    if not args.no_restore:
        print("Restoring NuGet packages...", flush=True)
        restore_exit = run([
            str(msbuild),
            str(solution),
            "/t:Restore",
            "/p:RestorePackagesConfig=true",
            "/m",
        ])
        if restore_exit != 0:
            print(f"Restore failed with exit code {restore_exit}.", file=sys.stderr)
            return restore_exit

    print(f"Building {args.configuration}|{args.platform}...", flush=True)
    build_exit = run([
        str(msbuild),
        str(solution),
        f"/p:Configuration={args.configuration}",
        f"/p:Platform={args.platform}",
        "/m",
    ])
    if build_exit != 0:
        print(f"Build failed with exit code {build_exit}.", file=sys.stderr)
        return build_exit

    output_dir = ROOT_DIR / args.platform / args.configuration / "HL2DinoPlugin"
    print()
    print("Build succeeded.")
    print("Outputs:")
    print(f"  {output_dir / 'HL2DinoPlugin.dll'}")
    print(f"  {output_dir / 'HL2DinoPlugin.winmd'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
