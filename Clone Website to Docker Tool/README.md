# cw2dt.py (Clone Website to Docker Tool)

This tool clones a website and packages it as a Docker-ready folder, with an optional step to build the Docker image. The workflow is fully automated and uses a modern PySide6 GUI.

## Features
- Clone any public website to a temporary cache
- Automatically generate Dockerfile and Nginx config
- Copy container files to your chosen destination
- Optionally build the Docker image (if Docker is installed)
- Console shows real-time verbose output
- Limit download size (MB/GB/TB)
- Throttle download speed (KB/s or MB/s)
- No web server or browser UI required

## Usage
1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
   - PySide6 and wget required.
   - **Windows:** Download wget from https://eternallybored.org/misc/wget/ and add to PATH.
   - **macOS:** Install wget via Homebrew: `brew install wget`
   - **Linux:** Install wget via your package manager: `sudo apt install wget` (Debian/Ubuntu) or `sudo yum install wget` (Fedora/RHEL)

2. Run the GUI:
   ```bash
   python cw2dt.py
   ```

3. Enter the website URL, Docker image name, and choose a destination folder.
4. (Optional) Enable download size cap and/or throttle speed.
5. Click "Clone Website & Prepare Docker Output".
6. (Optional) Enable Docker build if Docker is installed.
7. Find the output in your chosen folder, ready for Docker Desktop or CLI.

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