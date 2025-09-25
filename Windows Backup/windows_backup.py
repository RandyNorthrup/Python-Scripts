import os, sys, shutil, time, hashlib, datetime, json
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

        self.setWindowTitle("Windows Backup Application")
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

        # Set Backup Location Button (spans top row)
        self.backup_location_button = QPushButton("Set Backup Location", self)
        self.backup_location_button.clicked.connect(self.set_backup_location)
        layout.addWidget(self.backup_location_button, 0, 0, 1, cols)
        
        # De-Duplicate Button (next to backup location button)
        self.dedup_button = QPushButton("De-Duplicate", self)
        self.dedup_button.clicked.connect(self.run_deduplication)
        layout.addWidget(self.dedup_button, 0, 0, 7, cols)
        self.dedup_button.setFixedSize(180, 42)

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
            btn.setFixedSize(180, 42)
            btn.setEnabled(False)
            self.backup_buttons.append((btn, name))

            # --- Correct grid placement (fixes orientation/alignment) ---
            row = 2 + (idx // cols)      # first row after the header
            col = idx % cols             # 0, 1, 0, 1, ...
            layout.addWidget(btn, row, col)
            # ------------------------------------------------------------

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

        # Show a simple report dialog
        msg = "Duplicates found:\n"
        for _, paths in duplicates.items():
            msg += "\n".join(paths) + "\n------\n"
        QMessageBox.information(self, "Duplicates Found", msg)

        # Ask user for action using a dialog
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
            # Delete duplicates (keep first file)
            for _, paths in duplicates.items():
                for path in paths[1:]:
                    try:
                        os.remove(path)
                    except Exception as e:
                        QMessageBox.warning(self, "Delete Error", f"Failed to delete {path}: {e}")
            QMessageBox.information(self, "Done", "Duplicates deleted.")
        elif clicked == move_btn:
            # Ask for target directory
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
            # Ask for report file path
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
        if not self.backup_location:
            QMessageBox.warning(self, "Error", "Please set a backup location first.")
            return

        if not os.path.exists(source_dir):
            QMessageBox.warning(self, "Error", f"Source folder not found: {source_dir}")
            return

        destination_root = os.path.join(self.backup_location, destination_name)
        os.makedirs(destination_root, exist_ok=True)

        self.progress_dialog = QProgressDialog(f"Backing up {destination_name}...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumWidth(420)
        self.progress_dialog.setValue(0)

        self.worker = BackupWorker(source_dir, destination_root, patterns)
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
