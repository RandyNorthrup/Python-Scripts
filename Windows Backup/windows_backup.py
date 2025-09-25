import re
import sys
try:
    import plistlib
except ImportError:
    plistlib = None

# Windows-specific imports
if sys.platform.startswith("win"):
    try:
        import winreg
    except ImportError:
        winreg = None
import os, shutil, time, hashlib, datetime, json, threading, random
try:
    import win32api, win32con
except ImportError:
    win32api = win32con = None
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QPushButton, QWidget, QFileDialog, QMessageBox,
    QGridLayout, QProgressDialog, QSpacerItem, QSizePolicy
)
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import Qt, QThread, Signal, QTimer



def get_user_path(subpath=""):
    """Return full path inside user's profile directory."""
    user_profile = os.environ.get("USERPROFILE", "")
    return os.path.join(user_profile, subpath) if subpath else user_profile


class BackupWorker(QThread):
    progress_update = Signal(int, str, int, int, float)
    finished = Signal(int, bool, str)

    def __init__(self, source_dir, destination_root, patterns):
        super().__init__()
        self.source_dir = source_dir
        self.destination_root = destination_root
        self.patterns = patterns
        self.cancelled = False
        self.files_copied = 0
        self.total_size = 0
        self.copied_size = 0
        self.start_time = 0

    def run(self):
        try:
            total_files, total_size = self.count_files()
            self.total_size = total_size
            if total_files == 0:
                self.finished.emit(0, False, "No files found to backup.")
                return

            self.start_time = time.time()
            files_processed = 0

            for root, dirs, files in os.walk(self.source_dir):
                if self.cancelled:
                    break
                rel_path = os.path.relpath(root, self.source_dir)
                destination_folder = os.path.join(self.destination_root, rel_path)
                os.makedirs(destination_folder, exist_ok=True)

                for file in files:
                    if any(file.lower().endswith(p.lstrip("*").lower()) for p in self.patterns):
                        if self.cancelled:
                            break
                        source_file = os.path.join(root, file)
                        dest_file = os.path.join(destination_folder, file)
                        try:
                            file_size = os.path.getsize(source_file)
                            shutil.copy2(source_file, dest_file)
                            self.files_copied += 1
                            self.copied_size += file_size
                        except Exception as e:
                            self.finished.emit(self.files_copied, False, f"Failed to copy {file}: {e}")
                            return
                        files_processed += 1
                        elapsed_time = time.time() - self.start_time
                        speed = self.copied_size / (elapsed_time + 0.1)
                        self.progress_update.emit(files_processed, file, file_size, self.copied_size, speed)

            if self.cancelled:
                self.finished.emit(self.files_copied, False, "Backup cancelled by user.")
            else:
                self.finished.emit(self.files_copied, True, "Backup completed successfully.")

        except Exception as e:
            self.finished.emit(self.files_copied, False, f"Backup failed: {e}")

    def count_files(self):
        count = 0
        total_size = 0
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                if any(file.lower().endswith(p.lstrip("*").lower()) for p in self.patterns):
                    count += 1
                    total_size += os.path.getsize(os.path.join(root, file))
        return count, total_size

    def cancel(self):
        self.cancelled = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("S.A.K. Utility")
        self.setFixedSize(800, 600)
        self.backup_location = ""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout()
        central_widget.setLayout(layout)

        # --- Alignment/spacing tweaks for clean layout ---
        cols = 3
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        for c in range(cols):
            layout.setColumnStretch(c, 1)
        # -------------------------------------------------

        # Add Keep Screen On checkbox at the top
        self.setup_keep_screen_on(layout, 8, cols)

        # Add Dedupe Table (hidden by default, shown after scan)
        self.setup_dedupe_table(layout, 9, cols)

        # Set Backup Location Button (top row)
        self.backup_location_button = QPushButton("Set Backup Location", self)
        self.backup_location_button.setToolTip("Choose the folder where backups will be stored.")
        self.backup_location_button.clicked.connect(self.set_backup_location)
        layout.addWidget(self.backup_location_button, 0, 0, 1, cols)

        # Map buttons to (source path, patterns, destination name)
        self.backup_sources = {
            "Backup Contacts": (get_user_path("Contacts"), ["*"], "Contacts"),
            "Backup Photos": (get_user_path("Pictures"), ["*"], "Pictures"),
            "Backup Documents": (get_user_path("Documents"), ["*"], "Documents"),
            "Backup Videos": (get_user_path("Videos"), ["*"], "Videos"),
            "Backup Music": (get_user_path("Music"), ["*"], "Music"),
            "Backup Desktop": (get_user_path("Desktop"), ["*"], "Desktop"),
            "Backup Downloads": (get_user_path("Downloads"), ["*"], "Downloads"),
            "Backup Outlook Files": (get_user_path("AppData/Local/Microsoft/Outlook"),
                                     ["*.pst", "*.ost", "*.nst"], "Outlook"),
        }

        # Create buttons in a predictable left-to-right, top-to-bottom order
        self.backup_buttons = []
        for idx, (name, (src, pats, dest)) in enumerate(self.backup_sources.items()):
            btn = self.create_button(name, lambda checked=False, n=name: self.start_backup(*self.backup_sources[n]))
            btn.setToolTip(f"Backup all files from {src} to your backup location as '{dest}'.")
            btn.setFixedSize(180, 42)
            btn.setEnabled(False)
            self.backup_buttons.append((btn, name))

            # --- Correct grid placement (fixes orientation/alignment) ---
            row = 1 + (idx // cols)      # first row after the header
            col = idx % cols             # 0, 1, 2, ...
            layout.addWidget(btn, row, col)
            # ------------------------------------------------------------

        # Place Organize, De-Duplicate, and Scan License Keys buttons in a new row below backup buttons, with a blank row in between
        action_row = 2 + ((len(self.backup_sources) + cols - 1) // cols)
        # Add a blank spacer row (no widgets added to row action_row - 1)
        self.organize_button = QPushButton("Organize Directory", self)
        self.organize_button.setToolTip("Organize all files in a selected directory into subfolders by file extension.")
        self.organize_button.clicked.connect(self.organize_directory)
        self.organize_button.setFixedSize(180, 42)
        layout.addWidget(self.organize_button, action_row, 0)

        self.dedup_button = QPushButton("De-Duplicate", self)
        self.dedup_button.setToolTip("Scan a folder for duplicate files and take action on them.")
        self.dedup_button.clicked.connect(self.run_deduplication)
        self.dedup_button.setFixedSize(180, 42)
        layout.addWidget(self.dedup_button, action_row, 1)

        self.license_button = QPushButton("Scan for License Keys", self)
        self.license_button.setToolTip("Scan your system for software license keys and save a report.")
        self.license_button.clicked.connect(self.scan_for_license_keys)
        self.license_button.setFixedSize(180, 42)
        layout.addWidget(self.license_button, action_row, 2)

        # Add Select Users for Backup button below main action buttons
        self.selected_users = []  # List of user names selected for backup
        select_users_row = action_row + 1
        self.select_users_button = QPushButton("Select User(s) for Backup", self)
        self.select_users_button.setToolTip("Scan for user folders and select one or more for backup. Attempts to take ownership if needed.")
        self.select_users_button.clicked.connect(self.select_users_for_backup)
        self.select_users_button.setFixedSize(220, 42)
        layout.addWidget(self.select_users_button, select_users_row, 0, 1, cols)

        # Add a flexible spacer row below buttons to keep them top-aligned
        total_rows = 1 + ((len(self.backup_sources) + cols - 1) // cols)  # header + button rows
        layout.setRowStretch(total_rows + 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
               total_rows + 1, 0, 1, cols)

        # Auto-refresh timer every 5 seconds to re-check sources
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_source_folders)
        self.refresh_timer.start(5000)
    def select_users_for_backup(self):
        from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QListWidget, QPushButton, QAbstractItemView, QFileDialog
        import getpass
        import os
        import shutil
        user_root = os.path.expandvars(r"C:\Users") if sys.platform.startswith("win") else "/Users"
        current_user = getpass.getuser()
        # List user directories
        try:
            user_dirs = [d for d in os.listdir(user_root) if os.path.isdir(os.path.join(user_root, d))]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to list user directories: {e}")
            return
        if not user_dirs:
            QMessageBox.information(self, "No Users", "No user directories found.")
            return
        # Multi-select dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Select User(s) for Backup")
        vbox = QVBoxLayout(dlg)
        listw = QListWidget(dlg)
        listw.addItems(user_dirs)
        listw.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        vbox.addWidget(listw)
        ok_btn = QPushButton("OK", dlg)
        ok_btn.clicked.connect(dlg.accept)
        vbox.addWidget(ok_btn)
        dlg.setMinimumWidth(350)
        if not dlg.exec():
            return
        selected = [item.text() for item in listw.selectedItems()]
        if not selected:
            return
        self.selected_users = selected
        # Ask for backup location if not set
        backup_location = self.backup_location
        if not backup_location:
            backup_location = QFileDialog.getExistingDirectory(self, "Select Backup Location")
            if not backup_location:
                QMessageBox.warning(self, "Error", "No backup location selected.")
                return
            self.backup_location = backup_location
        # For each selected user, if not current, try to take ownership and copy
        for user in selected:
            user_path = os.path.join(user_root, user)
            if not os.path.exists(user_path):
                continue
            # Try to take ownership if not current user
            if user != current_user:
                if sys.platform.startswith("win"):
                    import subprocess
                    try:
                        takeown_cmd = ["takeown", "/f", user_path, "/r", "/d", "y"]
                        icacls_cmd = ["icacls", user_path, "/grant", f"{current_user}:F", "/t", "/c"]
                        subprocess.run(takeown_cmd, check=True, capture_output=True, shell=True)
                        subprocess.run(icacls_cmd, check=True, capture_output=True, shell=True)
                    except Exception as e:
                        res = QMessageBox.question(self, "Permission Error", f"Failed to take ownership of {user_path}: {e}\nContinue anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if res != QMessageBox.StandardButton.Yes:
                            continue
                else:
                    import subprocess
                    try:
                        subprocess.run(["sudo", "chown", "-R", current_user, user_path], check=True)
                        subprocess.run(["sudo", "chmod", "-R", "u+rwX", user_path], check=True)
                    except Exception as e:
                        res = QMessageBox.question(self, "Permission Error", f"Failed to take ownership of {user_path}: {e}\nContinue anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if res != QMessageBox.StandardButton.Yes:
                            continue
            # Copy user folder to backup location, preserving folder name
            dest_path = os.path.join(backup_location, user)
            try:
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(user_path, dest_path)
            except Exception as e:
                QMessageBox.warning(self, "Backup Error", f"Failed to backup {user}: {e}")
                continue
        QMessageBox.information(self, "Done", f"Selected user folders have been backed up to {backup_location}.")


    def organize_directory(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os, shutil
        # Prompt user for directory
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Organize")
        if not path:
            return
        # Confirm with the user before proceeding
        confirm = QMessageBox.question(self, "Confirm Organize", f"Are you sure you want to organize all files in:\n{path}\n? This will move files into subfolders by extension.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Error", "The specified directory does not exist.")
            return
        files = os.listdir(path)
        moved_count = 0
        for file in files:
            file_path = os.path.join(path, file)
            if os.path.isdir(file_path):
                continue
            filename, extension = os.path.splitext(file)
            extension = extension[1:] if extension else "NoExtension"
            dest_folder = os.path.join(path, extension)
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)
            dest_file_path = os.path.join(dest_folder, file)
            counter = 1
            while os.path.exists(dest_file_path):
                if extension != "NoExtension":
                    new_filename = f"{filename}{counter}.{extension}"
                else:
                    new_filename = f"{filename}_{counter}"
                dest_file_path = os.path.join(dest_folder, new_filename)
                counter += 1
            shutil.move(file_path, dest_file_path)
            moved_count += 1
        QMessageBox.information(self, "Organize Directory", f"Moved {moved_count} files into subfolders by extension.")
    def setup_dedupe_table(self, layout, row, cols):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QAbstractItemView
        self.dedupe_table = QTableWidget(self)
        self.dedupe_table.setColumnCount(2)
        self.dedupe_table.setHorizontalHeaderLabels(["Hash", "File Path"])
        self.dedupe_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dedupe_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dedupe_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.dedupe_table, row, 0, 1, cols)
        self.dedupe_table.hide()
    def scan_for_license_keys(self):
        all_data = {}
        if sys.platform.startswith("win"):
            all_data = self.scan_windows_registry()
        elif sys.platform.startswith("darwin"):
            if plistlib is None:
                QMessageBox.warning(self, "Error", "plistlib not available on this system.")
                return
            all_data = self.scan_macos_plists()
        else:
            QMessageBox.warning(self, "Error", "Unsupported platform for license key scan.")
            return

        if all_data:
            # Ask user where to save
            save_path, _ = QFileDialog.getSaveFileName(self, "Save License Keys Report", "licenses.json", "JSON Files (*.json);;All Files (*)")
            if not save_path:
                return
            def default_serializer(obj):
                try:
                    import datetime
                    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
                        return obj.isoformat()
                except Exception:
                    pass
                return str(obj)
            with open(save_path, "w") as f:
                json.dump(all_data, f, indent=4, default=default_serializer)
            QMessageBox.information(self, "Done", f"License keys saved to {save_path}")
        else:
            QMessageBox.information(self, "No Keys Found", "No license keys found or unsupported platform.")

    def scan_windows_registry(self):
        if not winreg:
            return {}
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows NT\CurrentVersion"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE"),
        ]
        results = {}
        for hive, path in registry_paths:
            try:
                reg_key = winreg.OpenKey(hive, path)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(reg_key, i)
                        if self.is_license_key(name, value):
                            results[f"{path}\\{name}"] = value
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(reg_key)
            except FileNotFoundError:
                continue
        return results

    def is_license_key(self, name, value):
        if isinstance(value, str):
            license_pattern = r"[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}"
            if "key" in name.lower() or "license" in name.lower() or re.search(license_pattern, value):
                return True
        return False

    def scan_macos_plists(self):
        results = {}
        search_paths = ["/Library/Preferences", os.path.expanduser("~/Library/Preferences")]
        for path in search_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith(".plist"):
                        file_path = os.path.join(path, file)
                        try:
                            with open(file_path, "rb") as f:
                                data = plistlib.load(f)
                                for k, v in data.items():
                                    if self.is_license_key(str(k), str(v)):
                                        results[f"{file}:{k}"] = v
                        except Exception:
                            continue
        return results

    def setup_keep_screen_on(self, layout, row, cols):
        from PySide6.QtWidgets import QCheckBox, QLabel
        self.keep_screen_on_checkbox = QCheckBox("Keep Screen On", self)
        self.keep_screen_on_checkbox.stateChanged.connect(self.toggle_keep_screen_on)
        layout.addWidget(self.keep_screen_on_checkbox, row, 0, 1, cols)
        self.keep_screen_on_thread = None
        self.keep_screen_on_running = False
        # Disable if not Windows or win32api unavailable
        if sys.platform != "win32" or not win32api or not win32con:
            self.keep_screen_on_checkbox.setEnabled(False)
            self.keep_screen_on_checkbox.setToolTip("This feature is only available on Windows with pywin32 installed.")

    def toggle_keep_screen_on(self, state):
        if state and win32api and win32con:
            self.keep_screen_on_running = True
            if not self.keep_screen_on_thread or not self.keep_screen_on_thread.is_alive():
                self.keep_screen_on_thread = threading.Thread(target=self.keep_screen_on_worker, daemon=True)
                self.keep_screen_on_thread.start()
        else:
            self.keep_screen_on_running = False

    def keep_screen_on_worker(self):
        while self.keep_screen_on_running:
            x = random.randint(0, 100)
            y = random.randint(0, 100)
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            time.sleep(15)
    def __init__(self):
        super().__init__()

        self.setWindowTitle("S.A.K. Utility")
        self.setFixedSize(800, 600)
        self.backup_location = ""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout()
        central_widget.setLayout(layout)

        # --- Alignment/spacing tweaks for clean layout ---
        cols = 3
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        for c in range(cols):
            layout.setColumnStretch(c, 1)
        # -------------------------------------------------


        # Add Keep Screen On checkbox at the top
        self.setup_keep_screen_on(layout, 8, cols)

        # Add Dedupe Table (hidden by default, shown after scan)
        self.setup_dedupe_table(layout, 9, cols)

        # Set Backup Location Button (top row)
        self.backup_location_button = QPushButton("Set Backup Location", self)
        self.backup_location_button.setToolTip("Choose the folder where backups will be stored.")
        self.backup_location_button.clicked.connect(self.set_backup_location)
        layout.addWidget(self.backup_location_button, 0, 0, 1, cols)

        # Map buttons to (source path, patterns, destination name)
        self.backup_sources = {
            "Backup Contacts": (get_user_path("Contacts"), ["*"], "Contacts"),
            "Backup Photos": (get_user_path("Pictures"), ["*"], "Pictures"),
            "Backup Documents": (get_user_path("Documents"), ["*"], "Documents"),
            "Backup Videos": (get_user_path("Videos"), ["*"], "Videos"),
            "Backup Music": (get_user_path("Music"), ["*"], "Music"),
            "Backup Desktop": (get_user_path("Desktop"), ["*"], "Desktop"),
            "Backup Downloads": (get_user_path("Downloads"), ["*"], "Downloads"),
            "Backup Outlook Files": (get_user_path("AppData/Local/Microsoft/Outlook"),
                                     ["*.pst", "*.ost", "*.nst"], "Outlook"),
        }

        # Create buttons in a predictable left-to-right, top-to-bottom order
        self.backup_buttons = []
        for idx, (name, (src, pats, dest)) in enumerate(self.backup_sources.items()):
            btn = self.create_button(name, lambda checked=False, n=name: self.start_backup(*self.backup_sources[n]))
            btn.setToolTip(f"Backup all files from {src} to your backup location as '{dest}'.")
            btn.setFixedSize(180, 42)
            btn.setEnabled(False)
            self.backup_buttons.append((btn, name))

            # --- Correct grid placement (fixes orientation/alignment) ---
            row = 1 + (idx // cols)      # first row after the header
            col = idx % cols             # 0, 1, 2, ...
            layout.addWidget(btn, row, col)
            # ------------------------------------------------------------

        # Place Organize, De-Duplicate, and Scan License Keys buttons in a new row below backup buttons, with a blank row in between
        action_row = 2 + ((len(self.backup_sources) + cols - 1) // cols)
        # Add a blank spacer row (no widgets added to row action_row - 1)
        self.organize_button = QPushButton("Organize Directory", self)
        self.organize_button.setToolTip("Organize all files in a selected directory into subfolders by file extension.")
        self.organize_button.clicked.connect(self.organize_directory)
        self.organize_button.setFixedSize(180, 42)
        layout.addWidget(self.organize_button, action_row, 0)

        self.dedup_button = QPushButton("De-Duplicate", self)
        self.dedup_button.setToolTip("Scan a folder for duplicate files and take action on them.")
        self.dedup_button.clicked.connect(self.run_deduplication)
        self.dedup_button.setFixedSize(180, 42)
        layout.addWidget(self.dedup_button, action_row, 1)

        self.license_button = QPushButton("Scan for License Keys", self)
        self.license_button.setToolTip("Scan your system for software license keys and save a report.")
        self.license_button.clicked.connect(self.scan_for_license_keys)
        self.license_button.setFixedSize(180, 42)
        layout.addWidget(self.license_button, action_row, 2)

        # Add Select Users for Backup button below main action buttons
        self.selected_users = []  # List of user names selected for backup
        select_users_row = action_row + 1
        self.select_users_button = QPushButton("Select User(s) for Backup", self)
        self.select_users_button.setToolTip("Scan for user folders and select one or more for backup. Attempts to take ownership if needed.")
        self.select_users_button.clicked.connect(self.select_users_for_backup)
        self.select_users_button.setFixedSize(220, 42)
        layout.addWidget(self.select_users_button, select_users_row, 0, 1, cols)
        # Add a flexible spacer row below buttons to keep them top-aligned
        total_rows = 1 + ((len(self.backup_sources) + cols - 1) // cols)  # header + button rows
        layout.setRowStretch(total_rows + 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
               total_rows + 1, 0, 1, cols)

        # Auto-refresh timer every 5 seconds to re-check sources
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_source_folders)
        self.refresh_timer.start(5000)

    def create_button(self, text, command):
        btn = QPushButton(text, self)
        btn.clicked.connect(command)
        return btn

    def set_backup_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Location")
        if folder:
            self.backup_location = folder
            self.check_source_folders()
            
    def run_deduplication(self):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QDialog, QVBoxLayout, QMessageBox, QPushButton
        # Use QFileDialog to select directory to scan
        directory = QFileDialog.getExistingDirectory(self, "Select Directory to Scan for Duplicates")
        if not directory:
            return  # User cancelled

        # For now, use default values for min_size and file_extensions
        min_size = 0
        file_extensions = None

        duplicates = self.find_duplicates(directory, min_size, file_extensions)
        if not duplicates:
            QMessageBox.information(self, "De-Duplicate", "No duplicates found.")
            return

        # Show results in a separate dialog window
        dialog = QDialog(self)
        dialog.setWindowTitle("Duplicate Files Found")
        dialog.setMinimumSize(700, 400)
        vbox = QVBoxLayout(dialog)
        table = QTableWidget(dialog)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Hash", "File Path"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setRowCount(0)
        for hash_val, paths in duplicates.items():
            for path in paths:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(hash_val))
                table.setItem(row, 1, QTableWidgetItem(path))
        table.resizeColumnsToContents()
        vbox.addWidget(table)
        # Add a close button
        close_btn = QPushButton("Close", dialog)
        close_btn.clicked.connect(dialog.accept)
        vbox.addWidget(close_btn)
        dialog.exec()

        # After dialog is closed, show the action dialog
        action_box = QMessageBox(self)
        action_box.setWindowTitle("Choose Action")
        action_box.setText("What would you like to do with the duplicates?")
        delete_btn = action_box.addButton("Delete Duplicates", QMessageBox.ButtonRole.AcceptRole)
        move_btn = action_box.addButton("Move Duplicates", QMessageBox.ButtonRole.ActionRole)
        report_btn = action_box.addButton("Save Report", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = action_box.addButton(QMessageBox.StandardButton.Cancel)
        action_box.exec()
        clicked = action_box.clickedButton()
        if clicked == delete_btn:
            for _, paths in duplicates.items():
                for path in paths[1:]:
                    try:
                        os.remove(path)
                    except Exception as e:
                        QMessageBox.warning(self, "Delete Error", f"Failed to delete {path}: {e}")
            QMessageBox.information(self, "Done", "Duplicates deleted.")
        elif clicked == move_btn:
            target_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Move Duplicates To")
            if not target_dir:
                return
            for _, paths in duplicates.items():
                for path in paths[1:]:
                    try:
                        target_path = os.path.join(target_dir, os.path.basename(path))
                        os.rename(path, target_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Move Error", f"Failed to move {path}: {e}")
            QMessageBox.information(self, "Done", "Duplicates moved.")
        elif clicked == report_btn:
            report_path, _ = QFileDialog.getSaveFileName(self, "Save Duplicates Report", "duplicates_report.json", "JSON Files (*.json);;All Files (*)")
            if not report_path:
                return
            self.generate_report(duplicates, report_path)
            QMessageBox.information(self, "Done", f"Report saved to {report_path}")
        else:
            QMessageBox.information(self, "No Action", "No action taken.")


    def get_file_hash(self, filepath):
        """Return the MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def find_duplicates(self, directory, min_size=0, file_extensions=None):
        """Find duplicate files in a directory, with optional file type filtering."""
        hashes = {}
        duplicates = {}
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                if file_extensions and not filename.lower().endswith(tuple(file_extensions)):
                    continue  # Skip files that don't match the extensions

                filepath = os.path.join(dirpath, filename)
                if os.path.getsize(filepath) >= min_size:
                    file_hash = self.get_file_hash(filepath)
                    if file_hash in hashes:
                        duplicates.setdefault(file_hash, []).append(filepath)
                        # Also ensure the original file is in the duplicates list
                        if hashes[file_hash] not in duplicates[file_hash]:
                            duplicates[file_hash].append(hashes[file_hash])
                    else:
                        hashes[file_hash] = filepath

        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    
    def generate_report(self, duplicates, report_path):
        """Generate a report of duplicate files in JSON format."""
        with open(report_path, 'w') as report_file:
            json.dump(duplicates, report_file, indent=4)
        print(f"Report generated: {report_path}")

    def check_source_folders(self):
        """Enable buttons only if source exists and has files; set tooltips if disabled"""
        for btn, name in self.backup_buttons:
            src, patterns, dest = self.backup_sources[name]
            folder_exists = os.path.exists(src)
            has_files = folder_exists and any(
                any(f.lower().endswith(p.lstrip("*").lower()) for f in files for p in patterns)
                for _, _, files in os.walk(src)
            )

            if folder_exists and has_files:
                if not btn.isEnabled():
                    btn.setEnabled(True)
                btn.setToolTip(f"Backup files from {src} → {dest}")
            else:
                if btn.isEnabled():
                    btn.setEnabled(False)
                if not folder_exists:
                    btn.setToolTip(f"Source folder not found: {src}")
                else:
                    btn.setToolTip(f"No files found in {src} to backup")


    def start_backup(self, source_dir, patterns, destination_name):
        import getpass
        import os
        from PySide6.QtWidgets import QProgressDialog, QMessageBox
        user_root = os.path.expandvars(r"C:\Users") if sys.platform.startswith("win") else "/Users"
        current_user = getpass.getuser()
        users = self.selected_users if self.selected_users else [current_user]
        for user in users:
            user_source_dir = source_dir.replace(get_user_path(), os.path.join(user_root, user))
            if not self.backup_location:
                QMessageBox.warning(self, "Error", "Please set a backup location first.")
                return
            if not os.path.exists(user_source_dir):
                QMessageBox.warning(self, "Error", f"Source folder not found: {user_source_dir}")
                continue
            destination_root = os.path.join(self.backup_location, user, destination_name)
            os.makedirs(destination_root, exist_ok=True)
            self.progress_dialog = QProgressDialog(f"Backing up {destination_name} for {user}...", "Cancel", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setMinimumWidth(420)
            self.progress_dialog.setValue(0)
            self.worker = BackupWorker(user_source_dir, destination_root, patterns)
            self.worker.progress_update.connect(self.update_progress)
            self.worker.finished.connect(self.backup_finished)
            self.progress_dialog.canceled.connect(self.worker.cancel)
            total_files, _ = self.worker.count_files()
            self.progress_dialog.setMaximum(total_files if total_files > 0 else 1)
            self.worker.start()

    def update_progress(self, value, filename, file_size, copied_size, speed):
        copied_mb = copied_size / (1024 * 1024)
        total_mb = self.worker.total_size / (1024 * 1024) if self.worker.total_size else 0
        speed_mb = speed / (1024 * 1024)
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(
            f"Copying: {filename}\n"
            f"File size: {file_size / 1024:.1f} KB\n"
            f"Copied: {copied_mb:.2f} / {total_mb:.2f} MB\n"
            f"Speed: {speed_mb:.2f} MB/s"
        )

    def backup_finished(self, files_copied, success, message):
        self.progress_dialog.close()
        if success:
            QMessageBox.information(self, "Success", f"{message}\n{files_copied} files backed up.")
        else:
            QMessageBox.warning(self, "Backup", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
