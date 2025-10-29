# Architecture Guide - VidDL

> **Referenced by**: `@AGENT.md`, `@GEMINI.md`

## Current Architecture

### Single-File Monolith (Current State)
**File**: `video_downloader_app.py` (900+ lines)

**Structure**:
```
VideoDownloaderApp (tk.Tk)
├── __init__()              # 100+ lines of UI construction
├── GUI Methods             # 30+ methods for UI interactions  
├── Download Methods        # Threading, yt-dlp integration
├── Player Methods          # VLC integration, playback control
├── Library Methods         # File browser, local playback
└── Visualizer Methods      # Audio visualization rendering
```

**Problems with current architecture**:
- ❌ Testing difficult (GUI tightly coupled to logic)
- ❌ Single Responsibility Principle violated
- ❌ Hard to modify one feature without affecting others
- ❌ No clear separation of concerns
- ❌ Difficult to reuse components

---

## Recommended Architecture

### Modular Structure (Target State)

```
videopull/
├── main.py                      # Entry point (10-20 lines)
├── core/
│   ├── __init__.py
│   ├── downloader.py            # yt-dlp wrapper
│   ├── queue_manager.py         # Download queue with threading
│   ├── player.py                # VLC wrapper
│   └── config.py                # Configuration management
├── gui/
│   ├── __init__.py
│   ├── main_window.py           # Main application window
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── download_panel.py   # Download UI components
│   │   ├── player_panel.py     # Player controls
│   │   ├── library_panel.py    # File browser
│   │   └── visualizer_panel.py # Audio visualizations
│   └── dialogs/
│       ├── __init__.py
│       ├── settings_dialog.py
│       └── about_dialog.py
├── utils/
│   ├── __init__.py
│   ├── sanitize.py              # Filename sanitization
│   ├── validators.py            # Input validation
│   └── formatters.py            # Time/size formatting
├── visualizers/
│   ├── __init__.py
│   ├── base.py                  # Base visualizer class
│   ├── bar.py                   # Bar visualizer
│   ├── spectrum.py              # Spectrum analyzer
│   ├── oscilloscope.py          # Oscilloscope mode
│   ├── heartbeat.py             # Heartbeat mode
│   └── three_d.py               # 3D visualization
└── tests/
    ├── __init__.py
    ├── test_downloader.py
    ├── test_sanitize.py
    └── test_player.py
```

---

## Component Responsibilities

### Core Layer (Business Logic)

#### `core/downloader.py`
**Responsibility**: Wrap yt-dlp with threading and error handling

```python
class VideoDownloader:
    """Handles video downloads with yt-dlp."""
    
    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.active_downloads = {}
        
    def download_video(
        self, 
        url: str, 
        output_path: str,
        format_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Download video in separate thread.
        
        Args:
            url: Video URL
            output_path: Save location
            format_id: Optional format ID
            progress_callback: Called with progress updates
            
        Returns:
            Download ID for tracking
        """
        
    def cancel_download(self, download_id: str) -> bool:
        """Cancel active download."""
        
    def pause_download(self, download_id: str) -> bool:
        """Pause active download."""
        
    def resume_download(self, download_id: str) -> bool:
        """Resume paused download."""
```

**Key patterns**:
- Thread management with `threading.Thread(daemon=True)`
- Progress reporting via callbacks
- Cancel/pause/resume using `threading.Event()`
- Error handling with retries

#### `core/queue_manager.py`
**Responsibility**: Manage download queue with worker pool

```python
class DownloadQueue:
    """Manages parallel downloads with worker threads."""
    
    def __init__(self, max_workers: int = 2):
        self.queue = queue.Queue()
        self.max_workers = max_workers
        self.workers = []
        self.active = False
        
    def add(self, url: str, options: dict) -> str:
        """Add download to queue, returns queue ID."""
        
    def start(self):
        """Start worker threads."""
        
    def stop(self):
        """Stop all workers gracefully."""
        
    def get_status(self) -> dict:
        """Get current queue status."""
```

**Pattern from Tartube/ytdlp-gui**:
- Use `queue.Queue` for thread-safe operations
- Limit to 2-3 workers (prevents rate limiting)
- Each worker polls queue with timeout

#### `core/player.py`
**Responsibility**: Wrap VLC with polling-based state management

```python
class MediaPlayer:
    """VLC media player with polling-based control."""
    
    def __init__(self, window_id: int):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.player.set_hwnd(window_id)
        self._position_callbacks = []
        self._update_job = None
        
    def load(self, filepath: str):
        """Load media file."""
        
    def play(self):
        """Start playback."""
        
    def pause(self):
        """Pause playback."""
        
    def seek(self, position_ms: int):
        """Seek to position in milliseconds."""
        
    def start_position_updates(self, interval_ms: int = 100):
        """Start polling VLC for position updates."""
        
    def register_position_callback(self, callback: Callable):
        """Register callback for position updates."""
```

**Critical pattern** (fixes seek bar bug):
```python
def _update_loop(self):
    """Poll VLC state and notify callbacks."""
    if self.player.is_playing():
        position = self.player.get_time()
        for callback in self._position_callbacks:
            callback(position)
    
    # Schedule next update
    self._update_job = self.root.after(100, self._update_loop)
```

### GUI Layer (Presentation)

#### `gui/main_window.py`
**Responsibility**: Coordinate UI components, handle window lifecycle

```python
class MainWindow(tk.Tk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.title("VidDL")
        self.geometry("900x800")
        
        # Initialize core components
        self.downloader = VideoDownloader(ffmpeg_path="./ffmpeg.exe")
        self.queue_manager = DownloadQueue(max_workers=2)
        self.player = None  # Created when player panel initializes
        
        # Build UI
        self._setup_ui()
        
        # Register cleanup
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _setup_ui(self):
        """Construct UI from panels."""
        self.download_panel = DownloadPanel(self, self.downloader)
        self.player_panel = PlayerPanel(self)
        self.library_panel = LibraryPanel(self)
        # Layout panels...
        
    def _on_closing(self):
        """Clean up resources before exit."""
        self.queue_manager.stop()
        if self.player:
            self.player.stop()
        self.destroy()
```

#### `gui/widgets/player_panel.py`
**Responsibility**: Player controls, seek bar, volume

```python
class PlayerPanel(ttk.Frame):
    """Media player controls panel."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.player = MediaPlayer(self.winfo_id())
        self.is_seeking = False
        self._build_ui()
        
    def _build_ui(self):
        """Construct player controls."""
        # Play/pause button
        self.play_button = ttk.Button(self, command=self._toggle_play)
        
        # Seek bar (CORRECTED PATTERN)
        self.seek_var = tk.DoubleVar()
        self.seek_slider = ttk.Scale(
            self, 
            from_=0, 
            to=100,
            variable=self.seek_var,
            command=None  # No command! Use events only
        )
        self.seek_slider.bind("<ButtonPress-1>", self._on_seek_start)
        self.seek_slider.bind("<ButtonRelease-1>", self._on_seek_end)
        
        # Volume slider (SEPARATE from seek)
        self.volume_var = tk.DoubleVar(value=100)
        self.volume_slider = ttk.Scale(
            self,
            from_=0,
            to=100,
            variable=self.volume_var,
            command=lambda v: self.player.set_volume(int(float(v)))
        )
        
        # Register for position updates
        self.player.register_position_callback(self._on_position_update)
        
    def _on_seek_start(self, event):
        """User started dragging seek bar."""
        self.is_seeking = True
        
    def _on_seek_end(self, event):
        """User released seek bar."""
        position = int(self.seek_var.get())
        self.player.seek(position)
        self.is_seeking = False
        
    def _on_position_update(self, position_ms: int):
        """Called by player when position changes."""
        if not self.is_seeking:  # Only update if not manually seeking
            self.seek_var.set(position_ms)
```

**This pattern completely separates seek and volume controls!**

### Utils Layer (Helpers)

#### `utils/sanitize.py`
**Responsibility**: Filename sanitization

```python
import re
import unicodedata

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for filesystem compatibility.
    
    Based on research from Tartube, ytdlp-gui, and yt-dlp-gui projects.
    
    Args:
        filename: Original filename
        max_length: Maximum length (default 200 chars)
        
    Returns:
        Safe filename for any filesystem
        
    Examples:
        >>> sanitize_filename("Video: Cool Stuff?")
        'Video- Cool Stuff'
        >>> sanitize_filename("データ/テスト")
        'データ-テスト'
    """
    # Normalize unicode (handles accents, special chars)
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Replace problematic characters
    replacements = {
        '/': '-',   # Path separator
        '\\': '-',  # Windows path separator
        ':': '-',   # Windows drive separator
        '*': '',    # Wildcard
        '?': '',    # Wildcard
        '"': "'",   # Quotes
        '<': '',    # Redirect
        '>': '',    # Redirect
        '|': '-',   # Pipe
    }
    
    for old, new in replacements.items():
        filename = filename.replace(old, new)
    
    # Collapse multiple spaces
    filename = re.sub(r'\s+', ' ', filename)
    
    # Remove leading/trailing problematic chars
    filename = filename.strip(' .-')
    
    # Enforce length limit
    if len(filename) > max_length:
        # Try to keep extension
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}"
        else:
            filename = filename[:max_length]
    
    return filename
```

---

## Threading Patterns

### Pattern 1: Simple Async Operation

```python
def start_download(self):
    """Initiate download without blocking GUI."""
    thread = threading.Thread(
        target=self._download_worker,
        args=(url, options),
        daemon=True
    )
    thread.start()

def _download_worker(self, url, options):
    """Worker function runs in separate thread."""
    try:
        result = download_video(url, options)
        # Update GUI safely
        self.after(0, lambda: self._on_download_complete(result))
    except Exception as e:
        self.after(0, lambda: self._on_download_error(str(e)))
```

### Pattern 2: Cancellable Operation

```python
class CancellableDownload:
    def __init__(self):
        self.cancel_flag = False
        
    def start(self):
        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()
        
    def cancel(self):
        self.cancel_flag = True
        
    def _worker(self):
        for chunk in download_chunks():
            if self.cancel_flag:
                return  # Exit thread
            process(chunk)
```

### Pattern 3: Pausable Operation

```python
class PausableDownload:
    def __init__(self):
        self.pause_event = threading.Event()
        self.pause_event.set()  # Initially not paused
        
    def pause(self):
        self.pause_event.clear()
        
    def resume(self):
        self.pause_event.set()
        
    def _worker(self):
        for chunk in download_chunks():
            self.pause_event.wait()  # Blocks if paused
            process(chunk)
```

### Pattern 4: Worker Pool with Queue

```python
class DownloadPool:
    def __init__(self, num_workers=2):
        self.queue = queue.Queue()
        self.workers = []
        self.active = True
        
        for _ in range(num_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
            
    def add_task(self, url, options):
        self.queue.put((url, options))
        
    def _worker(self):
        while self.active:
            try:
                url, options = self.queue.get(timeout=1)
                self._process_download(url, options)
                self.queue.task_done()
            except queue.Empty:
                continue
                
    def shutdown(self):
        self.active = False
        for worker in self.workers:
            worker.join(timeout=5)
```

---

## Migration Strategy

### Phase 1: Extract Utils (Low Risk)
1. Create `utils/sanitize.py`
2. Move filename sanitization logic
3. Update imports in main file
4. Test: Run application, download a video

**Benefit**: Immediate fix for filename bugs, minimal risk

### Phase 2: Extract Core (Medium Risk)
1. Create `core/downloader.py`
2. Move yt-dlp wrapper code
3. Keep interface identical
4. Update main file to use new class
5. Test: Download video, audio, playlist

**Benefit**: Testable download logic, cleaner separation

### Phase 3: Extract GUI Components (Higher Risk)
1. Create `gui/widgets/player_panel.py`
2. Move player UI code
3. Test player controls thoroughly
4. Repeat for other panels

**Benefit**: Modular UI, easier to modify

### Phase 4: Complete Separation (Highest Risk)
1. Create `gui/main_window.py`
2. Move window management
3. Wire everything together
4. Comprehensive testing

**Benefit**: Fully modular, testable, maintainable

---

## Testing Strategy

### Unit Tests (After Refactoring)

```python
# tests/test_sanitize.py
import pytest
from utils.sanitize import sanitize_filename

def test_removes_slashes():
    assert sanitize_filename("video/test") == "video-test"
    
def test_removes_colons():
    assert sanitize_filename("video:test") == "video-test"
    
def test_preserves_extension():
    result = sanitize_filename("a" * 250 + ".mp4", max_length=200)
    assert result.endswith(".mp4")
    assert len(result) <= 200

def test_unicode_normalization():
    assert sanitize_filename("café") == "cafe"
```

### Integration Tests (GUI)

```python
# tests/test_downloader_integration.py
import pytest
from core.downloader import VideoDownloader

def test_download_video():
    downloader = VideoDownloader("./ffmpeg.exe")
    
    # Use test URL or mock
    result = downloader.download_video(
        "https://test-url",
        "./test_output",
        format_id="best"
    )
    
    assert result is not None
    assert os.path.exists(result)
```

### GUI Tests (Challenging but possible)

```python
# tests/test_player_panel.py
import tkinter as tk
from gui.widgets.player_panel import PlayerPanel

def test_player_panel_creation():
    root = tk.Tk()
    panel = PlayerPanel(root)
    
    # Verify widgets created
    assert panel.play_button is not None
    assert panel.seek_slider is not None
    assert panel.volume_slider is not None
    
    root.destroy()
```

---

## Performance Considerations

### Memory Management
- **VLC instances**: Always call `.stop()` and `.release()`
- **Thread cleanup**: Use daemon threads, but still explicitly join on shutdown
- **Audio data**: Release numpy arrays after visualization

### CPU Optimization
- **Visualizer frame rate**: 25-30 FPS sufficient (not 50 FPS)
- **VLC polling**: 100ms interval optimal (not 20ms)
- **Thumbnail loading**: Use `Image.thumbnail()` not `Image.resize()`

### Network Optimization
- **Concurrent downloads**: Limit to 2-3 (prevents rate limiting)
- **Socket timeout**: 30 seconds reasonable
- **Retry logic**: Exponential backoff for network errors

---

## References

**Patterns sourced from**:
- **Tartube**: github.com/axcore/tartube (2,500+ stars)
- **ytdlp-gui**: github.com/aliencaocao/ytdlp-gui (Tkinter + yt-dlp)
- **yt-dlp-gui**: github.com/dsymbol/yt-dlp-gui (PySide6 + yt-dlp)

**Standards compliance**:
- PEP 8: Python style guide
- AGENTS.md: AI-friendly documentation
- Tkinter best practices
- Threading best practices

---

**Last updated**: Based on research of 10+ production video downloader projects
