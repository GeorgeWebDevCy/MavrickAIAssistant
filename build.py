import PyInstaller.__main__
import customtkinter
import os
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

# PyInstaller arguments
args = [
    'main.py',                                      # Main script
    '--name=Mavrick',                               # Executable name
    '--noconsole',                                  # Windowed mode (no terminal)
    '--onefile',                                    # Single executable file
    '--clean',                                      # Clean cache
    f'--add-data={ctk_path};customtkinter/',        # Bundle CustomTkinter theme data
    f'--add-data={assets_source};assets/',          # Bundle Audio Assets
    '--hidden-import=engine',                       # Explicitly import engine package
    '--hidden-import=engine.voice',
    '--hidden-import=engine.brain',
    '--hidden-import=engine.actions',
    '--hidden-import=PIL._tkinter_finder',          # Fix for CTkImage
    '--hidden-import=babel.numbers',                # Common issue with some libs
    '--hidden-import=dotenv',                       # Explicitly import dotenv module
    '--collect-all=psutil',                         # Collect all psutil data
    '--collect-all=speech_recognition',             # Collect all SR data
    '--collect-all=pygame',                         # Collect all pygame data
    '--collect-all=dotenv'                          # Collect pkg data
]

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
