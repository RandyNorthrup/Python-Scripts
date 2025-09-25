import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QMessageBox
from PIL import Image

class IconConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG to Icon Converter")
        self.setGeometry(200, 200, 300, 120)

        layout = QVBoxLayout()
        self.button = QPushButton("Select PNG and Convert")
        self.button.clicked.connect(self.convert_icon)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def convert_icon(self):
        # Step 1: Select PNG file
        png_file, _ = QFileDialog.getOpenFileName(self, "Select PNG File", "", "PNG Files (*.png)")
        if not png_file:
            return

        # Step 2: Ask where to save icons
        save_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if not save_dir:
            return

        try:
            img = Image.open(png_file).convert("RGBA")

            # Windows ICO
            ico_path = os.path.join(save_dir, "icon.ico")
            img.save(ico_path, format="ICO", sizes=[(16,16), (32,32), (48,48), (256,256)])

            # macOS ICNS
            icns_path = os.path.join(save_dir, "icon.icns")
            img.save(icns_path, format="ICNS")

            # Linux PNG sizes
            linux_sizes = [16, 24, 32, 48, 64, 128, 256, 512]
            linux_dir = os.path.join(save_dir, "linux_icons")
            os.makedirs(linux_dir, exist_ok=True)
            for size in linux_sizes:
                resized = img.resize((size, size), Image.LANCZOS)
                resized.save(os.path.join(linux_dir, f"icon_{size}x{size}.png"))

            QMessageBox.information(self, "Success", f"Icons saved in:\n{save_dir}")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IconConverterApp()
    window.show()
    sys.exit(app.exec())
