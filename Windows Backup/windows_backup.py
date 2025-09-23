import os, sys
from PySide6.QtWidgets import QMainWindow, QApplication, QPushButton, QVBoxLayout, QWidget, QFileDialog, QMessageBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Windows Backup Application")
        self.setFixedSize(800, 600)
        
        #Define Backup Location Variable
        self.backup_location = "" #Set by User
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        #Set Backup Location Button
        self.backup_location_button = QPushButton("Set Backup Location", self)
        self.backup_location_button.clicked.connect(self.set_backup_location)
        layout.addWidget(self.backup_location_button)
        
        
        #Create Backup Buttons
        self.backup_buttons = []
        
        self.backup_buttons.append(self.create_button("Backup Contacts", self.backup_contacts))
        self.backup_buttons.append(self.create_button("Backup Photos", self.backup_photos))
        self.backup_buttons.append(self.create_button("Backup Documents", self.backup_documents))
        self.backup_buttons.append(self.create_button("Backup Videos", self.backup_videos))
        self.backup_buttons.append(self.create_button("Backup Music", self.backup_music))
        self.backup_buttons.append(self.create_button("Backup Desktop", self.backup_desktop))
        self.backup_buttons.append(self.create_button("Backup Downloads", self.backup_downloads))

        for btn in self.backup_buttons:
            btn.setFixedSize(150, 40)  # Set button size
            btn.setEnabled(False)
            layout.addWidget(btn)            

           
            
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
                
    def run_backup(self, source, destination):
        if not self.backup_location:
            QMessageBox.warning(self, "Error", "Please set a backup location first.")
            return
        
        
        destination = os.path.join(self.backup_location, os.path.basename(source))
        os.makedirs(destination, exist_ok=True)
        cmd = f'xcopy /E /I /Y "{source}" "{destination}"'
        os.system(cmd)
        QMessageBox.information(self, "Success", f"Backup of {os.path.basename(source)} completed.")
        
    def backup_contacts(self):
        self.run_backup(os.path.expanduser("~/Contacts"))
        
    def backup_photos(self):
        self.run_backup(os.path.expanduser("~/Pictures"))
        
    def backup_documents(self):
        self.run_backup(os.path.expanduser("~/Documents"))
        
    def backup_videos(self):
        self.run_backup(os.path.expanduser("~/Videos"))
        
    def backup_music(self):
        self.run_backup(os.path.expanduser("~/Music"))
        
    def backup_desktop(self):
        self.run_backup(os.path.expanduser("~/Desktop"))
        
    def backup_downloads(self):
        self.run_backup(os.path.expanduser("~/Downloads"))
        
        
        
if __name__ == "__main__":       
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

