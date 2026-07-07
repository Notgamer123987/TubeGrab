# TubeGrab

A simple, clean desktop app to download YouTube videos in your preferred quality — built with Python and packaged as a native Windows app.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Paste any YouTube URL and fetch video info instantly (title, channel, views, thumbnail)
- Choose quality: 1080p, 720p, 480p, or extract audio only (MP3)
- Real-time download progress with speed and ETA
- Custom save folder (defaults to your Downloads folder)
- Download history panel
- Packaged as a native `.exe` with a proper Windows installer

## Installation


### Option 1: Download the installer (recommended)

1. Go to the [Releases](../../releases) page
2. Download `TubeGrabSetup.zip` from the latest release
3. Extract the zip
4. Run `TubeGrabSetup.exe` — it will install TubeGrab with Start Menu and Desktop shortcuts

### Option 2: Run from source

```bash
git clone https://github.com/Notgamer123987/TubeGrab.git
cd TubeGrab
pip install -r requirements.txt
python main.py
```

## Built With

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — modern UI toolkit for Python
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — video download engine
- [Pillow](https://python-pillow.org/) — image/thumbnail handling
- [PyInstaller](https://pyinstaller.org/) — packaging into a standalone `.exe`
- [Inno Setup](https://jrsoftware.org/isinfo.php) — Windows installer creation

## Requirements (for running from source)

```
customtkinter
pillow
yt-dlp
```

## Disclaimer

This tool is intended for downloading content you have the right to download (your own uploads, public domain content, or content where the creator permits downloads). Respect YouTube's Terms of Service and copyright law in your jurisdiction.

## License

MIT License — free to use, modify, and distribute.

## Author

Built by [Notgamer123987](https://github.com/Notgamer123987)