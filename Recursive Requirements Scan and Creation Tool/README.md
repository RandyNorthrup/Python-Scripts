# Recursive Requirements Scan and Creation Tool (RRSCT)

This tool provides a **Qt6 / PySide6 GUI** to recursively scan Python projects for dependencies and automatically create a clean, deduplicated `requirements.txt` file.
  
It scans:
- **First 50 lines** of all `.py` files for `import` and `from` statements.
- Any existing `requirements.txt` files.

Features:
- ✅ **GUI Interface** built with Qt6 / PySide6  
- ✅ **Recursive scanning** of directories  
- ✅ **Exclude standard library** option  
- ✅ **Automatic cleanup**: deduplication, removing local paths, handling version conflicts  
- ✅ **PyPI validation**: only valid packages remain  
- ✅ **Log panel** inside GUI for warnings and debug messages  

---

## Installation

Make sure you have Python 3.8+ installed.  
Install dependencies:

```bash
pip install PySide6 requests packaging
```

---

## Usage

Run the script:

```bash
python rrsct.py
```

### Steps:
1. **Select Source Directory** → Folder containing your Python project(s)  
2. **Select Destination** → Where to save the generated `requirements.txt`  
3. Optionally check **"Exclude standard libraries"**  
4. Click **Generate Master Requirements**  

The tool will:
- Scan `.py` and `requirements.txt` files recursively
- Deduplicate dependencies
- Validate packages on PyPI
- Show logs in the GUI
- Write the final list to `requirements.txt`

---

## Output

The generated `requirements.txt` will:
- Contain **only valid third-party dependencies**
- Deduplicate multiple versions, keeping the most restrictive or latest version
- Be directly usable with:

```bash
cat requirements.txt | xargs -n 1 pip install
Get-Content requirements.txt | ForEach-Object { pip install $_ }
```

---

## Example

Sample log output in the GUI:
```
Skipping invalid line: random_text_here
Package not on PyPI: custom_package
Could not read file: some_binary_file.txt
```

Final `requirements.txt` example:
```
numpy==1.26.4
pandas==2.2.3
requests>=2.31.0
PySide6==6.7.0
```

---

## Options

| Option                      | Description                                          |
|-----------------------------|------------------------------------------------------|
| **Exclude standard libraries** | Skips built-in Python modules like `os`, `sys`, etc. |
| **Log Panel**                | Shows skipped packages, errors, and warnings.        |

---

## Dependencies

- [PySide6](https://pypi.org/project/PySide6/) - Qt6 Python bindings  
- [requests](https://pypi.org/project/requests/) - for PyPI validation  
- [packaging](https://pypi.org/project/packaging/) - for version parsing  

Install all at once:

```bash
pip install PySide6 requests packaging
```

---

## Future Enhancements

- Save log output to a file  
- Group dependencies by source (`.py` vs `requirements.txt`)  
- Export results in multiple formats (CSV, JSON)  

---

**Author:** Randy Northrup

## License

MIT License - Feel free to use and modify.
