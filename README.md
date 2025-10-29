# VidDL
> A video/audio downloader and viewer for the people.

```

VidDL is a desktop application built with Python that allows you to download video and audio from various websites. It features an embedded media player to watch your downloaded content, complete with an audio visualizer for music.

## 🚀 Core Features

- **Modern GUI:** A clean, user-friendly interface built with Tkinter.
- **Metadata Display:** Fetches and displays the video's thumbnail, title, and duration before you download.
- **Guaranteed MP4 Output:** All video downloads are automatically converted to the universal MP4 format for maximum compatibility.
- **MP3 Audio Extraction:** Option to download only the audio from a video and save it as an MP3 file.
- **Embedded Video Player:** A stable, integrated VLC-based player.
- **Playback Controls:** Manual seek bar, play/pause, and volume controls.
- **Audio Visualizer:** A real-time, 2D bar-style visualizer for audio files.
- **Live Log Viewer:** A toggleable panel for monitoring and debugging.

## 🛠️ Requirements

- **Python 3**
- **yt-dlp:** For downloading.
- **python-vlc:** For the embedded player.
- **Pillow:** For image handling.
- **librosa & numpy:** For the audio visualizer.
- **ffmpeg:** Required for file conversion. Must be placed in the application's root directory (`ffmpeg.exe`).
- **VLC Media Player:** Must be installed on the system.

## 🏃 How to Run

1. Ensure all dependencies listed above are installed.
2. Place `ffmpeg.exe` in the same folder as the application.
3. Run the application from your terminal:
   ```sh
   python video_downloader_app.py
   ```
