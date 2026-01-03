import os
import sys

def _maybe_add_local_venv_site_packages():
    if sys.prefix != sys.base_prefix:
        return None
    project_root = os.path.dirname(os.path.abspath(__file__))
    for folder in ("venv", ".venv"):
        candidate = os.path.join(project_root, folder, "Lib", "site-packages")
        if os.path.isdir(candidate):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            return candidate
    return None

venv_site_packages = _maybe_add_local_venv_site_packages()
if venv_site_packages:
    print(f"Using local venv site-packages for build: {venv_site_packages}")

import PyInstaller.__main__
import customtkinter
import shutil

# Get customtkinter path for data inclusion
ctk_path = os.path.dirname(customtkinter.__file__)

# Define assets
assets_source = "assets"
assets_dest = "assets"

print("--- Mavrick AI Build Process Initiated ---")
print(f"CustomTkinter Location: {ctk_path}")

# Verify assets exist
if not os.path.exists(assets_source):
    print("WARNING: 'assets' folder not found. Audio features may fail.")

try:
    import pygame
except Exception as exc:
    print("ERROR: pygame is required for audio but could not be imported.")
    print("Install pygame in the build environment or run this script from the project venv.")
    raise SystemExit(1) from exc

# PyInstaller arguments
args = [
    'main.py',                                      # Main script
    '--name=Mavrick',                               # Executable name
    '--icon=assets/icon.ico',                       # Application Icon
    '--noconsole',                                  # Windowed mode (no terminal)
    '--onefile',                                    # Single executable file
    '--clean',                                      # Clean cache
    f'--add-data={ctk_path};customtkinter/',        # Bundle CustomTkinter theme data
    f'--add-data={assets_source};assets/',          # Bundle Audio Assets
    '--hidden-import=engine',                       # Explicitly import engine package
    '--hidden-import=engine.voice',
    '--hidden-import=engine.brain',
    '--hidden-import=engine.actions',
    '--hidden-import=engine.weather',
    '--hidden-import=PIL._tkinter_finder',          # Fix for CTkImage
    '--hidden-import=babel.numbers',                # Common issue with some libs
    '--hidden-import=dotenv',                       # Explicitly import dotenv module
    '--collect-all=psutil',                         # Collect all psutil data
    '--collect-all=speech_recognition',             # Collect all SR data
    '--collect-all=pygame',                         # Collect all pygame data
    '--collect-all=requests',                       # Collect requests data
    '--collect-all=dotenv'                          # Collect pkg data
]

if venv_site_packages:
    args.append(f'--paths={venv_site_packages}')

# Manually find and bundle dotenv
try:
    import dotenv
    dotenv_path = os.path.dirname(dotenv.__file__)
    print(f"Forcing bundle of dotenv from: {dotenv_path}")
    args.append(f'--add-data={dotenv_path};dotenv/')
except ImportError:
    print("WARNING: Could not resolve dotenv path for manual bundling.")

print("Running PyInstaller...")
PyInstaller.__main__.run(args)

print("--- Build Complete ---")
print("Executable is located in the 'dist' folder.")
print("IMPORTANT: Ensure your .env file is placed in the same directory as the executable.")
