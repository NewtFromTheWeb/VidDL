# VidDL - Developer & AI Agent Guide

## 🎯 Project Overview
**VidDL** is a feature-rich desktop media downloader and player.
- **Core Strategy**: High-performance downloads via `yt-dlp` Python API + Resilient VLC playback.
- **Visuals**: Modern neon-themed GUI (Cyberpunk, Hacker, Vaporwave) with real-time audio visualizations.
- **Target**: Universal compatibility (MP4/MP3) with advanced metadata preview.

## 🏗️ Technical Architecture
### 1. GUI Layer (`video_downloader_app.py`)
- **Framework**: Tkinter (standard) + `ttk` for styling.
- **Concurrency**: All blocking operations (fetching info, downloading) MUST run in daemon threads.
- **Thread Safety**: Never update the GUI directly from a thread. Use `self.after(0, callback)`.
- **Scaling**: Window is resizable with a minimum size of `1000x850` to prevent layout collapse.

### 2. Core Engine (`core/downloader.py`)
- **Library**: `yt-dlp` (Python API).
- **Format Selection**: Supports specific format IDs (passed from GUI) or fallback to `bestvideo+bestaudio`.
- **Resilience**: Configured with 20 retries and 30s socket timeouts to prevent stalling.
- **Sanitization**: All filenames are passed through `utils/sanitize.py` to prevent OS-level write errors.

### 3. Media Player & Visualizer
- **VLC Integration**: Uses `python-vlc`. Polling pattern (100ms) updates the seek bar.
- **Audio Processing**: `librosa` and `numpy` analyze local files for visualization. 
- **Streaming**: Previews use the direct URL from `yt-dlp` to avoid local disk writes before download.

---

## 🛠️ Maintenance Checklist

### Performance & Stability
- [ ] **Avoid Blocking**: Ensure `yt-dlp` calls are never on the main thread.
- [ ] **VLC Cleanup**: Always `release()` the VLC instance in `on_closing`.
- [ ] **ffmpeg.exe**: Must exist in the project root for merging/conversion.

### Theme & UI (Contrast Rules)
- [ ] **Checkbutton Contrast**: Ensure `TCheckbutton` foreground is bright on neon backgrounds.
- [ ] **Button States**: `active` background must be distinct from `normal` background.
- [ ] **Focus Management**: `Combobox` must be readable when focused.

### Download Features
- [ ] **Format Mapping**: Ensure resolution strings (e.g., "1080p") map correctly to format IDs.
- [ ] **Subtitles**: Toggle `--write-subs` and `--all-subs` based on user preference.
- [ ] **Retry Logic**: Keep `retries` high for unreliable network environments.

---

## 📂 Project Structure
```
VidDL/
├── core/
│   └── downloader.py      # Main yt-dlp wrapper (Resilience + Formats)
├── utils/
│   ├── sanitize.py        # Filename & OS path protector
│   └── __init__.py        # Package marker
├── ffmpeg.exe             # Required binary (do not delete)
├── video_downloader_app.py # Main GUI & Player Logic
├── requirements.txt       # Dependency list
├── README.md              # User documentation
└── AGENT.md               # This guide (Master Reference)
```

## 📜 Coding Patterns
### GUI Update Pattern
```python
def thread_safe_update(self, data):
    # Offload processing to background
    thread = threading.Thread(target=lambda: self._worker(data), daemon=True)
    thread.start()

def _worker(self, data):
    # Process...
    # Schedule GUI update back on main thread
    self.after(0, lambda: self.label.config(text="Done!"))
```

### Downloader Pattern
- Always pass a `progress_callback` to track real-time status.
- Use `restrictfilenames=True` in `yt-dlp` opts as a secondary safety layer.
