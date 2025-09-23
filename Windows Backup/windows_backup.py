import os, sys, glob, shutil
from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QFileDialog, QMessageBox, QGridLayout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Windows Backup Application")
        self.setFixedSize(800, 600)

        # Define Backup Location Variable
        self.backup_location = ""  # Set by User

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout()
        central_widget.setLayout(layout)
        cols = 2

        # Set Backup Location Button
        self.backup_location_button = QPushButton("Set Backup Location", self)
        self.backup_location_button.clicked.connect(self.set_backup_location)
        layout.addWidget(self.backup_location_button, 0, 0, 1, cols)  # Span top row

        # Create Backup Buttons
        self.backup_buttons = []
        self.backup_buttons.append(self.create_button("Backup Contacts", self.backup_contacts))
        self.backup_buttons.append(self.create_button("Backup Photos", self.backup_photos))
        self.backup_buttons.append(self.create_button("Backup Documents", self.backup_documents))
        self.backup_buttons.append(self.create_button("Backup Videos", self.backup_videos))
        self.backup_buttons.append(self.create_button("Backup Music", self.backup_music))
        self.backup_buttons.append(self.create_button("Backup Desktop", self.backup_desktop))
        self.backup_buttons.append(self.create_button("Backup Downloads", self.backup_downloads))
        self.backup_buttons.append(self.create_button("Backup Outlook Files", self.backup_outlook_files))

        # Add buttons to grid layout
        for idx, btn in enumerate(self.backup_buttons):
            btn.setFixedSize(150, 40)
            btn.setEnabled(False)
            row = 1 + idx // cols
            col = idx % cols
            layout.addWidget(btn, row, col)

    def create_button(self, text, command):
        btn = QPushButton(text, self)
        btn.clicked.connect(command)
        return btn

    def set_backup_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Location")
        if folder:
            self.backup_location = folder
            for btn in self.backup_buttons:
                btn.setEnabled(True)

    def copy_with_glob(self, source_dir, destination_name, patterns=["*"]):
        """Copy files matching patterns from source_dir to backup_location/destination_name"""
        if not self.backup_location:
            QMessageBox.warning(self, "Error", "Please set a backup location first.")
            return

        source_dir = os.path.expanduser(source_dir)
        if not os.path.exists(source_dir):
            QMessageBox.warning(self, "Error", f"Source folder not found: {source_dir}")
            return

        destination = os.path.join(self.backup_location, destination_name)
        os.makedirs(destination, exist_ok=True)

        files_copied = 0
        for pattern in patterns:
            for file_path in glob.glob(os.path.join(source_dir, pattern), recursive=True):
                if os.path.isfile(file_path):  # only copy files, not directories
                    try:
                        shutil.copy2(file_path, destination)
                        files_copied += 1
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to copy {file_path}: {e}")

        if files_copied > 0:
            QMessageBox.information(self, "Success", f"Backup of {files_copied} files completed in {destination_name}.")
        else:
            QMessageBox.information(self, "Info", f"No files found in {source_dir} to backup.")

    # Backup Methods
    def backup_contacts(self):
        self.copy_with_glob("~/Contacts", "Contacts")

    def backup_photos(self):
        self.copy_with_glob("~/Pictures", "Pictures")

    def backup_documents(self):
        self.copy_with_glob("~/Documents", "Documents")

    def backup_videos(self):
        self.copy_with_glob("~/Videos", "Videos")

    def backup_music(self):
        self.copy_with_glob("~/Music", "Music")

    def backup_desktop(self):
        self.copy_with_glob("~/Desktop", "Desktop")

    def backup_downloads(self):
        self.copy_with_glob("~/Downloads", "Downloads")

    def backup_outlook_files(self):
        self.copy_with_glob("~/AppData/Local/Microsoft/Outlook", "Outlook", ["*.pst", "*.ost", "*.nst"])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
