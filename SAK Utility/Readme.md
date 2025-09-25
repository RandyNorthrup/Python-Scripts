# Swiss Army Knife Utility

A simple GUI tool for backing up important user folders (Contacts, Photos, Documents, Videos, Music, Desktop, Downloads) to a user-selected location on Windows.

## Features

- Select a backup destination folder.
- One-click backup for each major user folder.
- Uses `xcopy` for fast, recursive copying.
- Built with PySide6 (Qt for Python).

## Requirements

- Python 3.x
- [PySide6](https://pypi.org/project/PySide6/)

Install dependencies:
```bash
pip install PySide6
```

## Usage

1. Open a terminal and navigate to the `Windows Backup` folder.
2. Run the script:
   ```bash
   python windows_backup.py
   ```
3. Click **Set Backup Location** and choose your backup destination.
4. Click any of the backup buttons (e.g., "Backup Documents") to back up that folder.

## Notes

- The script uses `xcopy`, which is available on Windows systems.
- Each backup creates a subfolder in your backup location with the same name as the source (e.g., "Documents").
- Make sure you have permission to read the source folders and write to the backup location.

## Disclaimer

Always verify your backups. The author is not responsible for any data loss.

## Created By:
- Randy Northrup
