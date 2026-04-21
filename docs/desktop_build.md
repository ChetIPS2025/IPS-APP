# IPS desktop launcher (PyWebView + PyInstaller)

## Run from source (recommended for development)

1. Create/activate the project virtualenv and install dependencies:

   ```text
   pip install -r requirements.txt -r requirements-desktop.txt
   ```

2. From the **repository root** (folder that contains `app/` and `desktop_launcher.py`):

   ```text
   python desktop_launcher.py
   ```

   This starts Streamlit on `http://127.0.0.1:<port>` (default **8501**, or the next free port) and opens a native **IPS App** window.

3. Optional environment variables:

   | Variable | Purpose |
   |----------|---------|
   | `IPS_LAUNCHER_DEBUG` | Set to `1` to print Streamlit stdout/stderr to the console (unfrozen runs). |
   | `IPS_STREAMLIT_PYTHON` | Full path to a `python.exe` that should run `python -m streamlit` (useful if the packaged EXE cannot launch Streamlit). |
   | `IPS_LAUNCHER_STREAMLIT_CONSOLE` | Set to `1` to show a Windows console for the Streamlit subprocess. |

## Build Windows onedir EXE

1. Same venv as above, from repo root:

   ```text
   pyinstaller --clean IPS_App.spec
   ```

2. Output layout:

   ```text
   dist/IPS_App/IPS_App.exe
   dist/IPS_App/_internal/   # bundled Python, streamlit, app copy, assets, static, .streamlit
   ```

3. Double-click **`IPS_App.exe`**. The launcher resolves `app/main.py` under `_internal/` (PyInstaller onedir layout).

4. **Frozen Streamlit subprocess:** the launcher uses `sys.executable -m streamlit`. Some PyInstaller layouts do not support `-m streamlit` from the same EXE. If the window shows a timeout error, install Streamlit into a normal Python and set **`IPS_STREAMLIT_PYTHON`** to that interpreter’s `python.exe`, then launch **`IPS_App.exe`** again.

## Icon

- EXE and window branding use **`static/ips_app.ico`** (multi-size ICO generated from the IPS PNG assets).
- Regenerate if needed:

  ```text
  python -c "from pathlib import Path; from PIL import Image; r=Path('.'); im=Image.open(r/'static'/'icon-512.png').convert('RGBA'); sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]; ims=[im.resize(s, Image.Resampling.LANCZOS) for s in sizes]; ims[0].save(r/'static'/'ips_app.ico', format='ICO', sizes=sizes)"
  ```

## Files involved

| File | Role |
|------|------|
| `desktop_launcher.py` | Subprocess Streamlit, wait for HTTP ready, PyWebView window, terminate child on exit |
| `IPS_App.spec` | PyInstaller onedir spec (`collect_all` for `streamlit` + `pywebview`, datas for `app/`, `assets/`, `static/`, `.streamlit/`) |
| `static/ips_app.ico` | Windows / PyInstaller icon |
| `app/main.py` | Streamlit entry (unchanged) |
