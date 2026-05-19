#!/usr/bin/env python3
"""
Helper script to find ADB installation and set ADB_PATH environment variable.
"""
import os
import subprocess
import sys
from pathlib import Path

def find_adb_in_common_locations():
    """Search for ADB in common installation locations."""
    common_paths = [
        "C:\\platform-tools\\adb.exe",
        "C:\\Android\\platform-tools\\adb.exe",
        "C:\\Program Files\\Android\\platform-tools\\adb.exe",
        "C:\\Users\\{}\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe".format(os.getenv("USERNAME", "")),
        "C:\\adb\\adb.exe",
    ]
    
    found_paths = []
    for path in common_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            found_paths.append(expanded_path)
    
    return found_paths

def find_adb_in_path():
    """Try to find ADB using 'where' command (Windows) or 'which' (Unix)."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(["where", "adb"], capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(["which", "adb"], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            return [p for p in paths if os.path.exists(p)]
    except:
        pass
    return []

def main():
    print("=" * 60)
    print("ADB Path Finder")
    print("=" * 60)
    print()
    
    # Check current ADB_PATH
    current_adb_path = os.getenv("ADB_PATH")
    if current_adb_path:
        print(f"[OK] ADB_PATH is currently set to: {current_adb_path}")
        if os.path.exists(current_adb_path):
            print("  [OK] Path exists and is valid")
            try:
                result = subprocess.run([current_adb_path, "version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"  [OK] ADB works: {result.stdout.strip().split()[0]}")
                else:
                    print("  [ERROR] ADB command failed")
            except Exception as e:
                print(f"  [ERROR] Error running ADB: {e}")
        else:
            print("  [ERROR] Path does not exist!")
        print()
    
    # Search in PATH
    print("Searching for ADB in system PATH...")
    path_results = find_adb_in_path()
    if path_results:
        print(f"[OK] Found ADB in PATH: {path_results[0]}")
    else:
        print("[ERROR] ADB not found in system PATH")
    print()
    
    # Search in common locations
    print("Searching in common installation locations...")
    common_results = find_adb_in_common_locations()
    if common_results:
        print(f"[OK] Found ADB in: {common_results[0]}")
        for path in common_results[1:]:
            print(f"  Also found: {path}")
    else:
        print("[ERROR] ADB not found in common locations")
    print()
    
    # Recommendations
    print("=" * 60)
    print("Recommendations:")
    print("=" * 60)
    
    all_paths = path_results + common_results
    if all_paths:
        recommended_path = all_paths[0]
        print(f"\n1. Use this ADB path: {recommended_path}")
        print("\n2. Set ADB_PATH environment variable:")
        print(f"   PowerShell (current session):")
        print(f'   $env:ADB_PATH="{recommended_path}"')
        print(f"\n   PowerShell (permanent - User):")
        print(f'   [Environment]::SetEnvironmentVariable("ADB_PATH", "{recommended_path}", "User")')
        print(f"\n   Command Prompt (current session):")
        print(f'   set ADB_PATH={recommended_path}')
        print(f"\n   Or add to system PATH:")
        print(f'   Add this directory to PATH: {os.path.dirname(recommended_path)}')
    else:
        print("\n[ERROR] ADB not found. Please:")
        print("  1. Download Android Platform Tools from:")
        print("     https://developer.android.com/studio/releases/platform-tools")
        print("  2. Extract to a folder (e.g., C:\\platform-tools)")
        print("  3. Set ADB_PATH to the full path of adb.exe")
        print("     Example: $env:ADB_PATH=\"C:\\platform-tools\\adb.exe\"")
    
    print("\n3. After setting ADB_PATH, restart your terminal and run:")
    print("   python main.py --list-devices")
    print()

if __name__ == "__main__":
    main()

