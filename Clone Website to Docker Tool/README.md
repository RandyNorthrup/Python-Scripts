# cw2dt.py (Clone Website to Docker Tool)

This tool clones a website and packages it as a Docker-ready folder, with an optional step to build the Docker image. The workflow is fully automated and uses a modern PySide6 GUI.

## Features
- Clone any public website to a temporary cache
- Automatically generate Dockerfile and Nginx config
- Copy container files to your chosen destination
- Optionally build the Docker image (if Docker is installed)
- Console shows real-time verbose output
- No web server or browser UI required

## Usage
1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
   (PySide6 and wget required. Install wget via Homebrew: `brew install wget`)

2. Run the GUI:
   ```bash
   python cw2dt.py
   ```

3. Enter the website URL, Docker image name, and choose a destination folder.
4. Click "Clone Website & Prepare Docker Output".
5. (Optional) Enable Docker build if Docker is installed.
6. Find the output in your chosen folder, ready for Docker Desktop or CLI.

## Notes
- The `cloned_sites` folder is used as a temporary cache and is cleared after each run.
- Only `cw2dt.py` and this README are required. Old web UI files have been removed.

## Requirements
- Python 3.8+
- PySide6
- wget (system utility)
- Docker (optional, for image build)

---
MIT License