# Build Instructions

This project is set up to be built as a standalone application for macOS and Windows.

## macOS Build

The macOS application has already been built using `MacBuild.spec`.
You can find the packaged app in:
`dist/TelegramScraper.app`

This `.app` bundle works standalone. You can zip it and share it with employees.
Note: Since it is not notarized, they may need to right-click > Open to bypass Gatekeeper initially.

### Re-building on Mac
To rebuild the Mac application:
```bash
pyinstaller --clean --noconfirm MacBuild.spec
```

## Windows Build

To create the standalone Windows executable (`.exe`), you must run the build on a Windows machine.

### Prerequisites (on Windows)
1.  **Python 3.10+** installed.
2.  **Tesseract OCR** installed or downloaded.
    *   Download Tesseract 5.x for Windows (e.g., from UB-Mannheim).
    *   Install it (e.g., to `C:\Program Files\Tesseract-OCR`) or extract the binaries.
3.  **Project Files**: Copy this entire project folder to the Windows machine.

### Setup Steps
1.  **Install Dependencies**:
    ```powershell
    pip install -r requirements.txt
    pip install pyinstaller
    ```

2.  **Prepare Binaries**:
    *   Create a folder `bin\win` in the project root.
    *   Copy the contents of your Tesseract installation (specifically `tesseract.exe` and all `.dll` files from the Tesseract installation folder) into `bin\win`.
    *   Ensure `tessdata` folder exists in project root with `eng.traineddata`.

3.  **Run Build**:
    ```powershell
    pyinstaller --clean --noconfirm WindowsBuild.spec
    ```

4.  **Result**:
    The standalone executable will be in `dist\TelegramScraper.exe`.
    You can distribute this single file to employees. It contains the configuration and Tesseract binaries.

## Configuration
The application bundles the `.env` file and uses hardcoded defaults in `config.py`, so end-users do not need to configure environment variables.
