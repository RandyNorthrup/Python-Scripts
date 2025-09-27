import sys
import os
import sysconfig
import re
import requests
from packaging.version import parse as parse_version, InvalidVersion
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QMessageBox, QProgressBar, QCheckBox, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal


# -------------------- HELPERS --------------------

def get_standard_libs():
    std_lib = sysconfig.get_paths()["stdlib"]
    std_libs = set()
    for root, _, files in os.walk(std_lib):
        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), std_lib)
                module = rel_path.replace(os.sep, ".").rsplit(".py", 1)[0]
                std_libs.add(module.split(".")[0])
    return std_libs


def clean_and_merge_requirements(reqs, log_fn):
    clean_reqs = {}
    pattern = re.compile(r"^([A-Za-z0-9_.\-]+)\s*([=<>!~]*.*)?$")

    for r in reqs:
        r = r.strip()
        if not r or r.startswith("#") or "@ file://" in r:
            continue

        match = pattern.match(r)
        if not match:
            log_fn(f"Skipping invalid line: {r}")
            continue

        pkg, spec = match.groups()
        pkg = pkg.lower()
        spec = spec.strip() if spec else ""

        if pkg in clean_reqs:
            old_spec = clean_reqs[pkg]
            try:
                if "==" in spec:
                    new_ver = spec.split("==")[-1]
                    old_ver = old_spec.split("==")[-1] if "==" in old_spec else ""
                    if not old_ver or parse_version(new_ver) > parse_version(old_ver):
                        clean_reqs[pkg] = spec
                else:
                    clean_reqs[pkg] = old_spec or spec
            except InvalidVersion:
                log_fn(f"Invalid version format for {pkg}: {spec}")
                clean_reqs[pkg] = spec or old_spec
        else:
            clean_reqs[pkg] = spec

    return [f"{pkg}{spec}" if spec else pkg for pkg, spec in sorted(clean_reqs.items())]


def validate_on_pypi(requirements, log_fn):
    valid_reqs = []
    for line in requirements:
        pkg = re.split(r"[=<>!~]", line)[0].strip()
        url = f"https://pypi.org/pypi/{pkg}/json"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                valid_reqs.append(line)
            else:
                log_fn(f"Package not on PyPI: {pkg}")
        except Exception:
            log_fn(f"Could not validate package: {pkg}")
    return valid_reqs


def safe_read_file(file_path, log_fn):
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            with open(file_path, "r", encoding=enc, errors="ignore") as f:
                return f.readlines()
        except Exception:
            continue
    log_fn(f"Could not read file: {file_path}")
    return []


# -------------------- WORKER THREAD --------------------

class Worker(QThread):
    progress = Signal(int)
    finished = Signal(list)
    log_msg = Signal(str)

    def __init__(self, source_dir, exclude_std):
        super().__init__()
        self.source_dir = source_dir
        self.exclude_std = exclude_std
        self.std_libs = get_standard_libs() if exclude_std else set()

    def log(self, message):
        self.log_msg.emit(message)

    def run(self):
        requirements = set()
        all_files = []
        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if file.endswith(".py") or file == "requirements.txt":
                    all_files.append(os.path.join(root, file))

        total_files = len(all_files)
        for idx, file_path in enumerate(all_files):
            if file_path.endswith(".py"):
                self.process_python_file(file_path, requirements)
            elif file_path.endswith("requirements.txt"):
                self.process_requirements_file(file_path, requirements)
            self.progress.emit(int((idx + 1) / total_files * 100))

        if self.exclude_std:
            requirements = {pkg for pkg in requirements if pkg not in self.std_libs}

        cleaned = clean_and_merge_requirements(requirements, self.log)
        validated = validate_on_pypi(cleaned, self.log)

        self.finished.emit(validated)

    def process_python_file(self, file_path, requirements):
        lines = safe_read_file(file_path, self.log)
        for i, line in enumerate(lines):
            if i >= 50:
                break
            line = line.strip()
            if line.startswith("import "):
                pkg = line.split()[1].split(".")[0]
                requirements.add(pkg)
            elif line.startswith("from "):
                pkg = line.split()[1].split(".")[0]
                requirements.add(pkg)

    def process_requirements_file(self, file_path, requirements):
        lines = safe_read_file(file_path, self.log)
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                requirements.add(line)


# -------------------- GUI --------------------

class RequirementsCollector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Master Requirements Generator")
        self.setGeometry(200, 200, 500, 400)

        layout = QVBoxLayout()

        self.select_src_btn = QPushButton("Select Source Directory")
        self.select_src_btn.clicked.connect(self.select_source_dir)
        layout.addWidget(self.select_src_btn)

        self.select_dest_btn = QPushButton("Select Destination for Master Requirements")
        self.select_dest_btn.clicked.connect(self.select_dest_file)
        layout.addWidget(self.select_dest_btn)

        self.exclude_std_cb = QCheckBox("Exclude standard libraries")
        layout.addWidget(self.exclude_std_cb)


        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.generate_btn = QPushButton("Generate Master Requirements")
        self.generate_btn.clicked.connect(self.generate_requirements)
        layout.addWidget(self.generate_btn)

        self.setLayout(layout)

        self.source_dir = ""
        self.dest_file = ""

    def select_source_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if dir_path:
            self.source_dir = dir_path

    def select_dest_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Master Requirements", "requirements.txt", "Text Files (*.txt)")
        if file_path:
            self.dest_file = file_path

    def generate_requirements(self):
        if not self.source_dir or not self.dest_file:
            QMessageBox.warning(self, "Error", "Please select both source directory and destination file.")
            return

        self.worker = Worker(self.source_dir, self.exclude_std_cb.isChecked())
    # Progress bar removed
        self.worker.log_msg.connect(self.log)
        self.worker.finished.connect(self.write_requirements)
        self.worker.start()

    def log(self, message):
        self.log_box.append(message)

    def write_requirements(self, requirements):
        try:
            with open(self.dest_file, "w") as f:
                for req in requirements:
                    f.write(req + "\n")
            QMessageBox.information(self, "Success", f"Master requirements.txt created at:\n{self.dest_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write file: {e}")


# -------------------- MAIN --------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RequirementsCollector()
    window.show()
    sys.exit(app.exec())
