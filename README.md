# Modified YouTube Comment Extractor

A modified Windows-friendly version of the YouTube Comment Extractor desktop app.

This version adds extra extraction and export features, including:

- Comments / Livechat selection
- Deep reply fetching
- Support for fetching replies under parent comments
- Faster comment-page delay
- TXT export for Notepad-friendly reading
- CSV and Excel exports
- Spam filtering options
- Date, likes, creator, and keyword filters

This project is a modified version of the original open-source project:

Original project: https://github.com/vijaykumarpeta/yt-comments-extractor

Please see the `LICENSE` file for licensing information.

---

## Download for Windows Users

The easiest way to use this modified version is to download the ready-made Windows ZIP from the **Releases** page.

### Windows EXE Download

1. Go to the **Releases** page of this repository.
2. Download:

```text
YouTube-Comment-Extractor-Windows.zip
```

3. Extract the ZIP file.
4. Open the extracted folder.
5. Double-click:

```text
YouTube Comment Extractor.exe
```

6. Enter your own YouTube Data API key.
7. Paste one or more YouTube video URLs.
8. Choose whether to extract:
   - Comments
   - Livechat
   - Both
9. Click **Go**.
10. Export results as CSV, TXT, or Excel.

No Python installation is needed if you use the Windows ZIP release.

---

## Run from Source Code

Use this method if you want to run or modify the Python source code.

### Clone this modified repository

```bash
git clone https://github.com/TigerXLight/modified-yt-comments-extractor.git
cd modified-yt-comments-extractor
```

### Create a virtual environment

```bash
python -m venv venv
```

### Activate the virtual environment

On Windows:

```bash
venv\Scripts\activate
```

On Mac/Linux:

```bash
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python main.py
```

---

## Basic Workflow

1. Launch the app.
2. Enter your YouTube Data API key in the sidebar.
3. Paste one or more YouTube video URLs.
4. Choose extraction mode:
   - **Comments** for normal video comments and replies
   - **Livechat** for live chat replay where available
   - Both if you want both types
5. Configure filters if needed:
   - Spam filter
   - Minimum likes
   - Sort by likes / newest / oldest
   - Exclude creator comments
   - Date range
   - Keyword filtering
6. Click **Go**.
7. Export results as:
   - CSV
   - TXT
   - Excel

---

## Supported YouTube URL Formats

The app supports common YouTube URL formats such as:

```text
https://www.youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/shorts/VIDEO_ID
https://www.youtube.com/embed/VIDEO_ID
```

You can paste multiple URLs, one per line.

---

## Export Formats

### CSV

Best for opening in spreadsheet programs like Excel, LibreOffice Calc, or Google Sheets.

### Excel

Exports the results into an `.xlsx` workbook.

### TXT

A Notepad-friendly readable format.

The TXT export is useful if you want to read comments and replies in a simple text layout rather than a spreadsheet.

Example TXT layout:

```text
[1] Parent Comment
Author: @ExampleUser
Date: 2026-07-02T00:35:12Z
Likes: 14
Reported replies: 2

Text:
  This is the main comment.

    ↳ Reply
    Author: @ReplyUser
    Date: 2026-07-02T00:40:01Z
    Likes: 3

    Text:
      This is a reply to the main comment.
```

---

## Replies Under Comments

This modified version is designed to fetch replies under parent comments, including comments with more than 100 replies.

For example, if a parent comment has 150+ replies, the extractor should keep requesting additional reply pages until the available replies are collected.

Important note: YouTube may still hide or withhold some comments/replies from the API if they are deleted, held for review, private, moderated, or otherwise unavailable.

---

## Sorting

The app includes sorting options:

- Likes
- Date (Newest)
- Date (Oldest)

For the best chance of seeing recent comments, choose:

```text
Date (Newest)
```

---

## API Key Requirement

This app requires a YouTube Data API key.

Each user should enter their own API key. Do not share your personal API key publicly.

If `keyring` is installed, the app can store the API key securely using your operating system credential manager.

Without secure keyring storage, the API key may be stored in a local settings file.

---

## Security Notes

Before uploading or sharing your own copy of this project, do not include:

```text
venv/
settings.json
.env
dist/
build/
__pycache__/
exported CSV, TXT, or Excel files
your personal API key
```

This repository should not contain any personal API keys.

---

## Windows Release Notes

The Windows release ZIP contains a bundled version of the app created with PyInstaller.

The ZIP normally contains:

```text
YouTube Comment Extractor.exe
_internal/
```

Keep the `.exe` and `_internal` folder together. Do not move the `.exe` out by itself, because it may need files inside `_internal`.

Some antivirus or Windows SmartScreen warnings can appear for unsigned homemade executables. This can happen with small open-source PyInstaller apps even when the app is safe.

---

## Main Modifications in This Version

Compared with the original project, this modified version includes:

- Added **Go** button with **Comments** and **Livechat** checkboxes
- Added support for choosing comments, livechat, or both
- Added deeper reply fetching
- Added TXT export for Notepad-friendly reading
- Reduced delay between comment pages
- Improved handling for replies and exports
- Added Windows-friendly launch workflow

---

## Development

To run from source:

```bash
python main.py
```

To build a Windows folder-based executable with PyInstaller:

```bash
pyinstaller --noconfirm --clean --windowed --name "YouTube Comment Extractor" --collect-all customtkinter --add-data "assets;assets" main.py
```

The built app will appear in:

```text
dist/YouTube Comment Extractor/
```

To zip the Windows build from CMD:

```cmd
powershell -NoProfile -Command "Compress-Archive -LiteralPath '.\dist\YouTube Comment Extractor' -DestinationPath '.\YouTube-Comment-Extractor-Windows.zip' -Force"
```

---

## Disclaimer

This tool uses the YouTube Data API. Results depend on what YouTube makes available through the API.

Some comments shown on the YouTube website may not be available through the API because of moderation, deletion, privacy, spam filtering, or other YouTube-side limitations.

This project is not affiliated with YouTube or Google.

---

## Credits

Original project by Vijay Kumar Peta:

https://github.com/vijaykumarpeta/yt-comments-extractor

Modified version maintained by TigerXLight.