# file: build_win.py

import subprocess
import json
import os
import platform

# --- Configuration ---

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    APP_NAME = config.get('meta', {}).get('name', 'Slothy Marker')
except (FileNotFoundError, json.JSONDecodeError):
    APP_NAME = 'Slothy Marker'

ENTRY_POINT = 'main.py'
ICON_FILE = os.path.join('icons', 'app-icon.ico')
OUTPUT_DIR = 'dist'
COLLECT_FILES_LIST = 'collect_files.txt'
COLLECT_FOLDERS_LIST = 'collect_folders.txt'

def read_list_from_file(filename):
    """
    Reads a list of paths from a text file.
    - Ignores empty lines.
    - Ignores lines starting with '#'.
    - Strips leading/trailing whitespace from each line.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            items = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith('#')
            ]
        print(f"Read {len(items)} items from '{filename}'.")
        return items
    except FileNotFoundError:
        print(f"Warning: Data collection file '{filename}' not found. No items will be collected from it.")
        return []

# Data files and folders to be included in the build.
# These are now read from external text files.
print("--- Reading data files and folders to bundle ---")
DATA_FILES = read_list_from_file(COLLECT_FILES_LIST)
DATA_FOLDERS = read_list_from_file(COLLECT_FOLDERS_LIST)

def build():
    """Runs the PyInstaller build command for Windows."""
    if platform.system() != "Windows":
        print("Error: This build script is intended for Windows only.")
        print("Please use build_mac.py for macOS.")
        exit(1)

    print(f"\n--- Starting Windows build for {APP_NAME} ---")

    # The separator for --add-data on Windows is ';'
    separator = ';'

    # Construct the PyInstaller command
    command = [
        'pyinstaller',
        '--noconfirm',      # Overwrite output directory without asking
        '--clean',          # Clean PyInstaller cache and remove temporary files before building
        '--name', APP_NAME,
        '--onefile',        # Create a single executable file for easy distribution
        '--windowed',       # Prevents a console window from appearing when the app is run
        '--icon', ICON_FILE,
    ]

    # Add data files. The destination '.' means they will be in the root of the bundle.
    for data_file in DATA_FILES:
        command.extend(['--add-data', f'{data_file}{separator}.'])

    # Add data folders. The destination is the same as the source folder name.
    for data_folder in DATA_FOLDERS:
        command.extend(['--add-data', f'{data_folder}{separator}{data_folder}'])

    # Add the main Python script
    command.append(ENTRY_POINT)

    # Print the full command for debugging purposes
    print("\nRunning command:")
    print(' '.join(f'"{c}"' if ' ' in c else c for c in command))

    # Execute the command
    try:
        print("\n--- PyInstaller Output ---")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')

        # Stream output to the console in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())

        return_code = process.poll()
        if return_code == 0:
            print("\n--- Build Successful! ---")
            print(f"Executable created at: {os.path.join(OUTPUT_DIR, f'{APP_NAME}.exe')}")
        else:
            print(f"\n--- Build FAILED! (PyInstaller exit code: {return_code}) ---")

    except FileNotFoundError:
        print("\n--- Build FAILED! ---")
        print("Error: 'pyinstaller' command not found.")
        print("Please ensure PyInstaller is installed in your Python environment (`pip install pyinstaller`).")
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")

if __name__ == '__main__':
    build()