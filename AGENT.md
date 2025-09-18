# Video Downloader Application

This project is a desktop application for downloading and playing videos from various websites. It is built using Python and the Tkinter library for the graphical user interface.

## Current Features

- **Modern GUI:** A clean, user-friendly interface built with the `ttk` themed widgets.
- **URL Processing:** Input any video URL supported by `yt-dlp`.
- **Metadata Display:** Fetches and displays the video's thumbnail, title, and duration before download.
- **Format Selection:** Fetch a list of available video qualities (e.g., 1080p, 720p, 480p) and choose the desired format for download.
- **Guaranteed MP4 Output:** All video downloads are automatically converted to the universal MP4 format (H.264/AAC) for maximum compatibility.
- **MP3 Audio Extraction:** Option to download only the audio from a video and save it as an MP3 file.
- **Directory Selection:** Browse and select a local directory to save downloaded files.
- **Embedded Video Player:** A fully integrated video player based on the VLC engine, embedded directly in the main window.
- **Advanced Playback Controls:**
  - Play/Pause button.
  - Manual Seek Bar: A draggable seek bar to jump to any point in the media.
  - Volume control slider.
- **Audio Visualizer:** A foundational 2D bar-style audio visualizer is included for audio-only files.
- **Live Log Viewer:** A toggleable panel shows the application's console output for debugging and monitoring.
- **Multithreaded Downloads:** The download process runs in a separate thread to keep the UI responsive.
- **Real-time Progress:** A progress bar and status label provide real-time feedback on the download process.
- **Error Handling:** Catches common errors (e.g., invalid URL, `ffmpeg` not found) and displays them to the user.

## Dependencies

- **Python 3**
- **Tkinter** (usually included with Python)
- **yt-dlp:** The core library for video downloading.
- **python-vlc:** The binding for the VLC media player engine.
- **Pillow:** Used for processing and displaying thumbnail images.
- **librosa & numpy:** Used for audio analysis for the visualizer.
- **ffmpeg:** Required for merging and converting video/audio streams. Must be present in the application's root directory (`ffmpeg.exe`).
- **VLC Media Player:** The VLC application must be installed on the user's system for the embedded player to function.