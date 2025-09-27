import sys
import os
import subprocess
import shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal

def docker_available():
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        return True
    except Exception:
        return False

class CloneThread(QThread):
    progress = Signal(str)
    finished = Signal(str)

    def __init__(self, url, docker_name, save_path, build_docker):
        super().__init__()
        self.url = url
        self.docker_name = docker_name
        self.save_path = save_path
        self.build_docker = build_docker

    def run(self):
        log = []
        def log_msg(msg):
            log.append(msg)
            self.progress.emit(msg)
        # Use cloned_sites as temp cache in script directory
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        cache_folder = os.path.join(script_dir, 'cloned_sites')
        if not os.path.exists(cache_folder):
            os.makedirs(cache_folder, exist_ok=True)
        temp_project_folder = os.path.join(cache_folder, self.docker_name)
        if os.path.exists(temp_project_folder):
            shutil.rmtree(temp_project_folder)
        os.makedirs(temp_project_folder, exist_ok=True)
        # Clone website using wget
        log_msg(f'Cloning {self.url} to {temp_project_folder}')
        wget_cmd = [
            'wget', '-e', 'robots=off', '--mirror', '--convert-links', '--adjust-extension', '--page-requisites', '--no-parent', self.url, '-P', temp_project_folder
        ]
        try:
            result = subprocess.run(wget_cmd, capture_output=True, text=True)
            log_msg(result.stdout)
            log_msg(result.stderr)
            if result.returncode != 0:
                log_msg(f'Error cloning website: {result.stderr}')
                self.finished.emit('\n'.join(log))
                shutil.rmtree(cache_folder)
                return
            log_msg('Cloning complete.')
        except Exception as e:
            log_msg(f'Error running wget: {e}')
            self.finished.emit('\n'.join(log))
            shutil.rmtree(cache_folder)
            return
        # Write Dockerfile
        dockerfile_path = os.path.join(temp_project_folder, 'Dockerfile')
        with open(dockerfile_path, 'w') as f:
            f.write('FROM nginx:alpine\nCOPY . /usr/share/nginx/html\nEXPOSE 80\nCMD ["nginx", "-g", "daemon off;"]\n')
        log_msg('Dockerfile created.')
        # Write nginx.conf
        nginx_conf_path = os.path.join(temp_project_folder, 'nginx.conf')
        with open(nginx_conf_path, 'w') as f:
            f.write('# Default Nginx config. Edit as needed.\n')
        # Write README
        readme_path = os.path.join(temp_project_folder, f'README_{self.docker_name}.md')
        with open(readme_path, 'w') as f:
            f.write(f"""# Docker Website Container\n\nThis folder contains a complete website clone and Dockerfile, ready to be built into a Docker image on any device with Docker installed.\n\n## Files\n- Dockerfile\n- nginx.conf (optional, for advanced config)\n- Website files (images, videos, assets)\n\n## How to Use\n1. On a Docker-enabled device, open a terminal in this folder.\n2. Build the image:\n   - docker build -t {self.docker_name} .\n3. (Optional) Save/export the image as a tar for Docker Desktop:\n   - docker save -o {self.docker_name}.tar {self.docker_name}\n4. To run the container:\n   - docker run -d -p 8080:80 {self.docker_name}\n   - (Change port as needed)\n5. The website will be served by Nginx at http://localhost:8080\n\n## Advanced\n- You can edit nginx.conf and rebuild the image if needed.\n- The Dockerfile is included for reference or customization.\n\n---\n""")
        log_msg(f'README created: {readme_path}')
        # Copy to chosen destination
        output_folder = os.path.join(self.save_path, self.docker_name)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        shutil.copytree(temp_project_folder, output_folder)
        log_msg(f'Container files copied to: {output_folder}')
        # Optionally build Docker image
        if self.build_docker:
            if docker_available():
                log_msg('Building Docker image...')
                build_cmd = ['docker', 'build', '-t', self.docker_name, output_folder]
                try:
                    result = subprocess.run(build_cmd, capture_output=True, text=True)
                    log_msg(result.stdout)
                    log_msg(result.stderr)
                    if result.returncode != 0:
                        log_msg(f'Docker build failed: {result.stderr}')
                    else:
                        log_msg('Docker build complete.')
                except Exception as e:
                    log_msg(f'Error building Docker image: {e}')
            else:
                log_msg('Docker is not installed or not available in PATH.')
        # Clean up cache
        shutil.rmtree(cache_folder)
        self.finished.emit('\n'.join(log))

class DockerClonerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Clone Website to Docker Tool')
        self.setGeometry(100, 100, 600, 600)
        layout = QVBoxLayout()

        layout.addWidget(QLabel('Website URL:'))
        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)

        layout.addWidget(QLabel('Docker Image Name:'))
        self.docker_name_input = QLineEdit()
        layout.addWidget(self.docker_name_input)

        layout.addWidget(QLabel('Destination Folder:'))
        hbox = QHBoxLayout()
        self.save_path_display = QLineEdit()
        self.save_path_display.setReadOnly(True)
        hbox.addWidget(self.save_path_display)
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self.browse_folder)
        hbox.addWidget(browse_btn)
        layout.addLayout(hbox)

        self.build_checkbox = QCheckBox('Build Docker image after clone (requires Docker)')
        layout.addWidget(self.build_checkbox)

        self.start_btn = QPushButton('Clone Website & Prepare Docker Output')
        self.start_btn.clicked.connect(self.start_clone)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)

        layout.addWidget(QLabel('Console Log:'))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        self.setLayout(layout)
        # Disable Docker build and image name if Docker is not available
        if not docker_available():
            self.build_checkbox.setEnabled(False)
            self.docker_name_input.setEnabled(False)
            self.build_checkbox.setToolTip('Docker not found. Install Docker to enable this feature.')
            self.docker_name_input.setToolTip('Docker not found. Install Docker to enable this feature.')
        # Enable/disable clone button based on required fields
        self.url_input.textChanged.connect(self.update_button_state)
        self.save_path_display.textChanged.connect(self.update_button_state)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        if folder:
            self.save_path_display.setText(folder)

    def update_button_state(self):
        url = self.url_input.text().strip()
        save_path = self.save_path_display.text().strip()
        self.start_btn.setEnabled(bool(url and save_path))

    def start_clone(self):
        url = self.url_input.text().strip()
        docker_name = self.docker_name_input.text().strip()
        save_path = self.save_path_display.text().strip()
        build_docker = self.build_checkbox.isChecked()
        # Prevent Docker build if Docker name is empty and build is checked
        if build_docker and not docker_name:
            self.console.append('Docker image name is required to build the image.')
            return
        self.console.clear()
        self.clone_thread = CloneThread(url, docker_name, save_path, build_docker)
        self.clone_thread.progress.connect(self.update_console)
        self.clone_thread.finished.connect(self.clone_finished)
        self.clone_thread.start()

    def update_console(self, msg):
        self.console.append(msg)
        self.console.ensureCursorVisible()

    def clone_finished(self, log):
        self.console.append('\nProcess finished.')
        self.console.ensureCursorVisible()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DockerClonerGUI()
    window.show()
    sys.exit(app.exec())
