# Code Examples and Patterns - VidDL

> **Referenced by**: `@AGENT.md`, `@GEMINI.md`, `@ARCHITECTURE.md`

This document provides concrete examples of good and bad code patterns for the VidDL project, with explanations of why each pattern works or fails. All examples are based on research from production Python video downloader projects and Python best practices.

---

## Threading Patterns

### ✅ GOOD: Non-blocking Download with Daemon Thread

```python
def download_video(self):
    """Start download in background thread to keep GUI responsive."""
    if not self.download_dir:
        self.status_label.config(text="Error: Select download directory first")
        return
    
    # Disable button to prevent multiple simultaneous downloads
    self.download_button.config(state="disabled")
    
    # Start download in daemon thread
    thread = threading.Thread(
        target=self.download_thread,
        args=(url, options),
        daemon=True  # ✅ Daemon threads exit when main program exits
    )
    thread.start()

def download_thread(self, url, options):
    """Worker function runs in separate thread."""
    try:
        # Heavy download operation here
        result = perform_download(url, options)
        
        # ✅ Update GUI safely using after()
        self.after(0, lambda: self.on_download_complete(result))
    except Exception as e:
        # ✅ Safe error handling with GUI update
        self.after(0, lambda: self.on_download_error(str(e)))
    finally:
        # ✅ Re-enable button safely
        self.after(0, lambda: self.download_button.config(state="normal"))
```

**Why this works**:
- GUI remains responsive during download
- Daemon thread automatically stops if app closes
- All GUI updates wrapped in `self.after()` for thread safety
- Error handling prevents thread crashes
- Button state managed properly

### ❌ BAD: Blocking Download

```python
def download_video(self):
    """Download video - BLOCKS GUI!"""
    # ❌ This runs in main thread
    result = perform_download(url, options)
    self.status_label.config(text="Done")
```

**Why this fails**:
- GUI freezes during download (can't click anything)
- Application appears to hang
- User can't cancel operation
- Poor user experience

### ❌ BAD: Direct GUI Update from Thread

```python
def download_thread(self):
    """Download in thread but update GUI directly."""
    result = perform_download()
    # ❌ Direct GUI update from non-main thread
    self.status_label.config(text="Done")
```

**Why this fails**:
- Tkinter is not thread-safe
- Causes crashes or undefined behavior
- Works sometimes, fails randomly
- Extremely hard to debug

---

## VLC Integration Patterns

### ✅ GOOD: Polling-Based Position Updates

```python
class PlayerPanel:
    def __init__(self, parent):
        self.parent = parent
        self.player = vlc.MediaPlayer()
        self.is_seeking = False
        self._position_update_job = None
        
    def start_playback(self):
        """Start playing and begin position updates."""
        self.player.play()
        self.start_position_updates()
        
    def start_position_updates(self):
        """Poll VLC for position updates."""
        self._update_position()
        
    def _update_position(self):
        """Internal method that polls VLC state."""
        if self.player.is_playing() and not self.is_seeking:
            # Get current position
            position = self.player.get_time()
            length = self.player.get_length()
            
            if length > 0:
                # Update seek slider
                self.seek_var.set(position)
                
                # Update time display
                current = time.strftime('%M:%S', time.gmtime(position / 1000))
                total = time.strftime('%M:%S', time.gmtime(length / 1000))
                self.time_label.config(text=f"{current} / {total}")
        
        # Schedule next update (100ms interval)
        self._position_update_job = self.parent.after(100, self._update_position)
        
    def stop_position_updates(self):
        """Stop polling (cleanup)."""
        if self._position_update_job:
            self.parent.after_cancel(self._position_update_job)
            self._position_update_job = None
```

**Why this works**:
- Predictable behavior (polls every 100ms)
- No event synchronization issues
- `is_seeking` flag prevents updates during manual seeking
- Easy to start/stop
- Based on production app patterns (Tartube, ytdlp-gui)

### ❌ BAD: VLC Event-Based Updates

```python
def setup_player(self):
    """Setup player with event handling."""
    self.player = vlc.MediaPlayer()
    
    # ❌ Try to use VLC events
    event_manager = self.player.event_manager()
    event_manager.event_attach(
        vlc.EventType.MediaPlayerTimeChanged,
        self.on_time_changed
    )
    
def on_time_changed(self, event):
    """Called by VLC when time changes."""
    # ❌ This may fire too frequently or not at all
    # ❌ May cause threading issues
    position = self.player.get_time()
    self.seek_var.set(position)
```

**Why this fails**:
- VLC events unreliable in Python binding
- May fire too frequently (performance issues)
- May not fire at all (missed updates)
- Threading issues with Tkinter
- Unpredictable across different VLC versions

---

## Seek Bar Control Patterns

### ✅ GOOD: Separate Seek and Volume Controls

```python
def setup_controls(self):
    """Setup player controls with proper separation."""
    # Seek slider - uses events ONLY, no command
    self.seek_var = tk.DoubleVar()
    self.seek_slider = ttk.Scale(
        self.controls_frame,
        from_=0,
        to=1000000,
        orient="horizontal",
        variable=self.seek_var,
        command=None  # ✅ No command parameter
    )
    # Bind events for manual seeking
    self.seek_slider.bind("<ButtonPress-1>", self.on_seek_start)
    self.seek_slider.bind("<ButtonRelease-1>", self.on_seek_end)
    self.seek_slider.pack()
    
    # Volume slider - uses command, separate from seek
    self.volume_var = tk.DoubleVar(value=100)
    self.volume_slider = ttk.Scale(
        self.controls_frame,
        from_=0,
        to=100,
        orient="horizontal",
        variable=self.volume_var,
        command=lambda v: self.player.audio_set_volume(int(float(v)))  # ✅ Command OK here
    )
    self.volume_slider.pack()

def on_seek_start(self, event):
    """User started dragging seek bar."""
    self.is_seeking = True  # Block automatic updates
    
def on_seek_end(self, event):
    """User released seek bar."""
    position = int(self.seek_var.get())
    self.player.set_time(position)
    self.is_seeking = False  # Resume automatic updates
```

**Why this works**:
- Clear separation: seek uses events, volume uses command
- No feedback loops
- `is_seeking` flag prevents conflicts
- Volume control works independently
- Seek bar responds to both manual and automatic updates

### ❌ BAD: Both Use Command Parameter

```python
def setup_controls(self):
    """Setup controls - PROBLEMATIC."""
    # Seek slider
    self.seek_slider = ttk.Scale(
        self.controls_frame,
        variable=self.seek_var,
        command=self.on_seek_command  # ❌ Fires on ANY change
    )
    self.seek_slider.bind("<ButtonPress-1>", self.on_seek_start)
    
    # Volume slider
    self.volume_slider = ttk.Scale(
        self.controls_frame,
        variable=self.volume_var,
        command=self.set_volume  # Also uses command
    )

def update_position(self):
    """Automatic position updates."""
    pos = self.player.get_time()
    self.seek_var.set(pos)  # ❌ Triggers on_seek_command!
```

**Why this fails**:
- Setting seek_var triggers command (feedback loop)
- Automatic updates interfere with manual seeking
- Events conflict with command
- Creates unpredictable behavior
- Volume and seek logic get entangled

---

## Filename Sanitization Patterns

### ✅ GOOD: Unicode Normalization + Character Replacement

```python
import re
import unicodedata

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for filesystem compatibility.
    
    Args:
        filename: Original filename (may contain illegal chars)
        max_length: Maximum length (default 200)
        
    Returns:
        Safe filename for any filesystem
    """
    # ✅ Normalize unicode (handles accents, emoji)
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # ✅ Replace illegal characters
    replacements = {
        '/': '-', '\\': '-', ':': '-', '*': '',
        '?': '', '"': "'", '<': '', '>': '', '|': '-'
    }
    for old, new in replacements.items():
        filename = filename.replace(old, new)
    
    # ✅ Collapse whitespace
    filename = re.sub(r'\s+', ' ', filename)
    
    # ✅ Trim problematic chars
    filename = filename.strip(' .-')
    
    # ✅ Enforce length limit
    if len(filename) > max_length:
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}"
        else:
            filename = filename[:max_length]
    
    # ✅ Handle empty result
    return filename if filename else "untitled"

# Usage
sanitized = sanitize_filename("Video: Cool Stuff? 🔥")
# Result: "Video- Cool Stuff "
```

**Why this works**:
- Handles all illegal filesystem characters
- Unicode normalization prevents encoding issues
- Preserves file extension
- Enforces reasonable length limits
- Never returns empty string
- Based on production patterns

### ✅ GOOD: Use yt-dlp's Built-in Sanitization

```python
def download_video(self, url, output_path):
    """Download with automatic filename sanitization."""
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'restrictfilenames': True,  # ✅ yt-dlp handles sanitization
        'ffmpeg_location': self.ffmpeg_path,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
```

**Why this works**:
- Leverages yt-dlp's battle-tested sanitization
- No custom code to maintain
- Handles all edge cases automatically
- Cross-platform compatible

### ❌ BAD: No Sanitization

```python
def download_video(self, url, output_path):
    """Download without sanitization - BREAKS."""
    ydl_opts = {
        # ❌ Uses raw title with illegal characters
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])  # ❌ OSError for illegal characters
```

**Why this fails**:
- Crashes on videos with `:`, `/`, `?`, etc. in title
- Unicode characters cause issues
- ~10% of downloads fail
- Error messages are cryptic

---

## Resource Cleanup Patterns

### ✅ GOOD: Proper Cleanup on Exit

```python
class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Setup...
        
        # ✅ Register cleanup handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """Clean up all resources before exit."""
        print("Cleaning up...")
        
        # ✅ Cancel scheduled callbacks
        if self.visualizer_update_job:
            self.after_cancel(self.visualizer_update_job)
        
        # ✅ Stop and release VLC
        if self.media_player:
            try:
                self.media_player.stop()
                self.media_player.release()
            except Exception as e:
                print(f"VLC cleanup error: {e}")
        
        # ✅ Release VLC instance
        if self.vlc_instance:
            try:
                self.vlc_instance.release()
            except Exception as e:
                print(f"VLC instance cleanup error: {e}")
        
        # ✅ Set flags for threads to stop
        self.is_visualizing = False
        
        print("Cleanup complete")
        
        # ✅ Destroy window
        self.destroy()
```

**Why this works**:
- Registered cleanup runs before window closes
- VLC resources properly released
- Callbacks cancelled (prevents errors)
- Threads notified to stop
- Error handling prevents cleanup crashes

### ❌ BAD: No Cleanup

```python
class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Setup...
        # ❌ No cleanup handler registered
```

**Why this fails**:
- VLC processes remain after close
- Memory leaks accumulate
- Callbacks continue firing (errors)
- Application doesn't exit cleanly

---

## Error Handling Patterns

### ✅ GOOD: User-Friendly Error Messages

```python
def download_video(self):
    """Download with proper error handling."""
    if not self.download_dir:
        # ✅ Clear, actionable error message
        self.status_label.config(
            text="Error: Please select a download directory first"
        )
        return
    
    if not os.path.exists("./ffmpeg.exe"):
        # ✅ Specific error with solution
        self.status_label.config(
            text="Error: ffmpeg.exe not found. Place it in the project folder."
        )
        self.download_button.config(state="disabled")
        return
    
    # Start download...

def download_thread(self, url, options):
    """Download worker with error handling."""
    try:
        result = self.download_with_ytdlp(url, options)
        self.after(0, lambda: self.on_success(result))
        
    except yt_dlp.utils.DownloadError as e:
        # ✅ Specific error type handling
        error_msg = str(e)
        if "HTTP Error 429" in error_msg:
            msg = "Rate limited. Please wait a few minutes."
        elif "Video unavailable" in error_msg:
            msg = "Video not available (deleted or private)"
        else:
            msg = f"Download error: {error_msg}"
        
        self.after(0, lambda: self.status_label.config(text=msg))
        
    except Exception as e:
        # ✅ Generic error fallback
        print(f"Unexpected error: {e}")  # For debugging
        self.after(0, lambda: self.status_label.config(
            text=f"Error: {str(e)}"
        ))
```

**Why this works**:
- Clear error messages for users
- Specific handling for common errors
- Debugging info in console
- Graceful degradation
- GUI always updated safely

### ❌ BAD: Silent Failures

```python
def download_video(self):
    """Download without error handling - SILENT FAILURES."""
    try:
        result = perform_download()
        # Success path...
    except:
        pass  # ❌ Silently ignore all errors
```

**Why this fails**:
- User has no idea what went wrong
- Impossible to debug
- Errors go unnoticed
- Poor user experience

---

## Configuration Patterns

### ✅ GOOD: Centralized Configuration

```python
# config.py
import os

class Config:
    """Application configuration."""
    
    # Paths
    FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg.exe")
    DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads/VidDL")
    
    # Download settings
    MAX_CONCURRENT_DOWNLOADS = 2
    SOCKET_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Player settings
    VLC_CACHE_SIZE = 2000  # milliseconds
    POSITION_UPDATE_INTERVAL = 100  # milliseconds
    
    # Visualizer settings
    VISUALIZER_FPS = 25
    VISUALIZER_UPDATE_INTERVAL = 40  # milliseconds (1000/25)
    FFT_CHUNK_SIZE = 2048
    
    @staticmethod
    def validate():
        """Validate configuration."""
        if not os.path.exists(Config.FFMPEG_PATH):
            raise FileNotFoundError("ffmpeg.exe not found")
        return True

# Usage in main app
from config import Config

class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Validate configuration
        try:
            Config.validate()
        except FileNotFoundError as e:
            self.show_error(str(e))
            
        # Use configuration
        self.vlc_instance = vlc.Instance(f"--file-caching={Config.VLC_CACHE_SIZE}")
```

**Why this works**:
- Single source of truth
- Easy to modify settings
- Validation in one place
- Type-safe values
- Clear documentation

### ❌ BAD: Magic Numbers Everywhere

```python
def __init__(self):
    """Initialize with magic numbers scattered."""
    self.vlc_instance = vlc.Instance("--file-caching=2000")  # ❌ Magic number
    self.after(100, self.update)  # ❌ What is 100?
    
def visualize(self):
    chunk_size = 2048  # ❌ Why 2048?
    self.after(40, self.visualize)  # ❌ Why 40?
```

**Why this fails**:
- Hard to understand
- Hard to modify consistently
- No centralized configuration
- Values scattered throughout code

---

## Type Hints and Documentation

### ✅ GOOD: Well-Documented Function

```python
from typing import Optional, Callable, List, Dict, Any

def download_video(
    url: str,
    output_path: str,
    format_id: Optional[str] = None,
    extract_audio: bool = False,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> str:
    """
    Download video from URL.
    
    Args:
        url: Video URL (YouTube, TikTok, Reddit, etc.)
        output_path: Directory to save downloaded file
        format_id: Optional format ID (default: best quality)
        extract_audio: If True, extract audio as MP3
        progress_callback: Optional function called with progress updates
                          Receives dict with keys: downloaded_bytes, total_bytes, speed, eta
    
    Returns:
        Path to downloaded file
        
    Raises:
        DownloadError: If download fails
        FileNotFoundError: If output_path doesn't exist
        
    Examples:
        >>> download_video("https://youtube.com/watch?v=...", "./downloads")
        './downloads/Video Title.mp4'
        
        >>> download_video("https://youtube.com/watch?v=...", "./downloads", extract_audio=True)
        './downloads/Video Title.mp3'
    """
    # Implementation...
```

**Why this works**:
- Clear parameter types
- Comprehensive documentation
- Usage examples
- Error documentation
- IDE autocomplete support

### ❌ BAD: No Documentation

```python
def download_video(url, path, fmt=None, audio=False, cb=None):
    # Implementation...
    pass
```

**Why this fails**:
- Unclear what parameters do
- No type information
- No usage examples
- Hard to use correctly

---

## Initialization Patterns

### ✅ GOOD: All Attributes Initialized

```python
class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        """Initialize application with all attributes."""
        super().__init__()
        
        # Window properties
        self.title("VidDL")
        self.geometry("900x800")
        
        # File paths
        self.download_dir: Optional[str] = None
        self.downloaded_file_path: Optional[str] = None
        
        # Download state
        self.formats: List[Dict[str, Any]] = []
        self.playlist_videos: List[Dict[str, Any]] = []
        self.is_playlist: bool = False
        
        # Playback state
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.is_seeking: bool = False
        self.is_playing_from_library: bool = False  # ✅ Initialize all flags
        
        # VLC
        self.vlc_instance = vlc.Instance("--file-caching=2000")
        self.media_player = self.vlc_instance.media_player_new()
        
        # Visualizer
        self.is_visualizing: bool = False
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: Optional[int] = None
        self.visualizer_update_job: Optional[str] = None
        
        # Continue with UI setup...
```

**Why this works**:
- All attributes declared in one place
- Clear types with type hints
- No AttributeError surprises
- Easy to see all instance state
- IDE autocomplete works

### ❌ BAD: Attributes Created Randomly

```python
class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VidDL")
        # ❌ Some attributes initialized, others not
        
    def some_method(self):
        # ❌ Attribute created on first use
        self.is_playing_from_library = False
        
    def another_method(self):
        # ❌ Crashes if some_method never called
        if self.is_playing_from_library:
            pass
```

**Why this fails**:
- AttributeError if methods called in wrong order
- Hard to track all instance state
- No single source of truth
- Difficult to understand class interface

---

## Summary of Patterns

### Do These ✅
- Use daemon threads for background work
- Update GUI with `self.after()` from threads
- Poll VLC state instead of using events
- Separate seek slider (events) from volume slider (command)
- Sanitize filenames with unicode normalization
- Register cleanup handler with `protocol("WM_DELETE_WINDOW", ...)`
- Initialize all attributes in `__init__`
- Add type hints and docstrings
- Handle errors with user-friendly messages
- Use configuration classes

### Don't Do These ❌
- Block main thread with long operations
- Update GUI directly from worker threads
- Use VLC events for position updates
- Use `command` parameter on seek slider
- Trust video titles as filenames
- Skip cleanup handlers
- Create attributes randomly throughout code
- Skip documentation
- Silently ignore errors
- Scatter magic numbers everywhere

---

**Based on**: Research from Tartube, ytdlp-gui, yt-dlp-gui, and Python best practices  
**Last updated**: October 2025
