# VidDL - AI Agent Instructions

> **Note**: This file follows the AGENTS.md standard supported by Claude Code, GitHub Copilot, Cursor, and 20+ other AI coding tools.

## 📋 Quick Reference
- **Main file**: `video_downloader_app.py`
- **Tech stack**: Python 3 + Tkinter + yt-dlp + VLC + librosa
- **Dependencies**: See `requirements.txt` (if it exists) or inline imports
- **Critical resources**: `ffmpeg.exe` must be in project root
- **Detailed guidance**: See `@ARCHITECTURE.md`, `@BUGS_AND_SOLUTIONS.md`, `@CODE_EXAMPLES.md`

---

## 🎯 Project Overview

**VidDL** is a desktop video/audio downloader with embedded playback for personal use. It downloads from YouTube, TikTok, Reddit, and any site supported by yt-dlp, then plays content in an integrated VLC player with audio visualizations.

**Core capabilities**:
- Download video (MP4) or audio (MP3) from any URL
- Playlist/channel batch downloads with checkboxes
- Embedded VLC media player with seek/pause/volume
- Multiple audio visualizer modes (bar, spectrum, oscilloscope, 3D, heartbeat)
- Local media library browser
- Real-time download progress with threading

**Current architecture**: Single-file monolithic (900+ lines). See `@ARCHITECTURE.md` for recommended refactoring.

---

## 🏗️ Project Structure

```
videopull/
├── video_downloader_app.py    # Main application (all code)
├── ffmpeg.exe                  # Required for format conversion
├── AGENT.md                    # This file
├── GEMINI.md                   # Gemini CLI specific instructions
├── ARCHITECTURE.md             # Detailed patterns and structure
├── BUGS_AND_SOLUTIONS.md       # Known issues with fixes
├── CODE_EXAMPLES.md            # Good/bad patterns reference
└── CODE_REVIEW_NOTES.md        # Original code review findings
```

**Recommended refactoring** (see `@ARCHITECTURE.md`):
```
video_downloader/
├── core/
│   ├── downloader.py      # yt-dlp wrapper with threading
│   ├── queue_manager.py   # Download queue management
│   └── player.py          # VLC wrapper with polling
├── gui/
│   ├── main_window.py     # Main Tkinter window
│   └── widgets/           # Custom widgets
└── utils/
    ├── sanitize.py        # Filename sanitization
    └── validators.py      # Input validation
```

---

## 🔧 Environment Setup

### Required Dependencies
```bash
pip install yt-dlp python-vlc Pillow librosa numpy
```

### System Requirements
- **VLC Media Player**: Must be installed on system
- **ffmpeg.exe**: Must be in project root directory
- **Python 3.7+**: Required for f-strings and type hints

### Run Application
```bash
python video_downloader_app.py
```

---

## 📝 Development Workflow

### Code Quality (File-scoped)
```bash
# Format code (when you create formatting tools)
black video_downloader_app.py

# Lint code (when you add linting)
ruff check video_downloader_app.py

# Type check (when you add type hints)
mypy video_downloader_app.py
```

### Testing Strategy
**Current state**: No automated tests
**Recommended**: See `@ARCHITECTURE.md` for testing patterns

### Version Control
```bash
# Before committing
git status
git add <files>
git commit -m "feat: descriptive message"
git push origin master
```

---

## 🎨 Coding Conventions

### Style Guide
- **PEP 8 compliant**: Standard Python style
- **Line length**: 100 characters (current code uses 100+, acceptable for Tkinter)
- **Indentation**: 4 spaces
- **Naming**:
  - Classes: `PascalCase` (e.g., `VideoDownloaderApp`)
  - Methods/functions: `snake_case` (e.g., `fetch_url_info`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_DOWNLOAD_THREADS`)
  - Private methods: `_leading_underscore` (e.g., `_download_worker`)

### Tkinter-Specific Patterns
- **Always use daemon threads**: `threading.Thread(..., daemon=True)`
- **GUI updates from threads**: Use `self.after(0, lambda: self.widget.config(...))`
- **Never block main thread**: All yt-dlp operations in separate threads
- **Use ttk widgets**: Prefer `ttk.Button` over `tk.Button` for modern look

### Threading Safety Rules
```python
# ✅ CORRECT: Update GUI from thread safely
def download_thread(self):
    data = download_video()
    self.after(0, lambda: self.status_label.config(text="Done"))

# ❌ WRONG: Direct GUI update from thread
def download_thread(self):
    data = download_video()
    self.status_label.config(text="Done")  # WILL CRASH!
```

### Error Handling
- **Always catch exceptions**: Especially in threads
- **User-friendly messages**: Show errors in GUI, details in log
- **Resource cleanup**: Use try/finally for VLC and threads

**See `@CODE_EXAMPLES.md` for complete good/bad patterns**

---

## 🐛 Known Issues & Solutions

**Critical bugs** (see `@BUGS_AND_SOLUTIONS.md` for details):

1. **Seek bar acts as volume control** (HIGH PRIORITY)
   - Root cause: Event binding conflict between seek and volume sliders
   - Solution: Use VLC polling pattern instead of event callbacks

2. **Missing attribute `is_playing_from_library`** (HIGH PRIORITY)
   - Root cause: Not initialized in `__init__`
   - Solution: Add `self.is_playing_from_library = False` in `__init__`

3. **Filename sanitization missing** (MEDIUM PRIORITY)
   - Root cause: Special characters in titles cause filesystem errors
   - Solution: Implement unicode normalization + character replacement

4. **No resource cleanup on exit** (MEDIUM PRIORITY)
   - Root cause: VLC and threads persist after window close
   - Solution: Add `on_closing()` method with cleanup

**See `@BUGS_AND_SOLUTIONS.md` for complete bug list with code solutions**

---

## 🔒 Permission Boundaries

### Safe Operations (No Approval Needed)
✅ Read any project file
✅ Run the application for testing
✅ Modify `video_downloader_app.py` to fix bugs
✅ Create new `.md` documentation files
✅ Add comments and docstrings
✅ Print debug information
✅ Create new Python files for refactoring

### Requires Explicit Approval
❌ Delete any files
❌ Modify `ffmpeg.exe` or binary files
❌ Install new system dependencies
❌ Run system commands beyond Python
❌ Make breaking API changes
❌ Modify `.git` directory
❌ Change project structure drastically without discussion

### Internet Operations
⚠️ **Web searches**: Allowed for research (e.g., yt-dlp documentation)
⚠️ **Package downloads**: Ask before suggesting new dependencies

---

## 📚 Reference Examples

### Threading Patterns
**See full examples in `@CODE_EXAMPLES.md`**

Good: Daemon threads with GUI callbacks
```python
def download_video(self):
    thread = threading.Thread(target=self.download_thread, daemon=True)
    thread.start()

def download_thread(self):
    # Heavy work here
    self.after(0, lambda: self.update_progress(100))
```

### VLC Integration
**See full examples in `@CODE_EXAMPLES.md`**

Good: Polling pattern for position updates
```python
def update_seek_slider(self):
    if self.media_player.is_playing():
        pos = self.media_player.get_time()
        self.seek_var.set(pos)
    self.after(100, self.update_seek_slider)
```

### File Operations
**See full examples in `@CODE_EXAMPLES.md`**

Good: Sanitize filenames before saving
```python
def sanitize_filename(filename):
    # Remove illegal characters
    return re.sub(r'[<>:"/\\|?*]', '_', filename)
```

---

## 🎯 Implementation Priorities

When working on this project, follow this priority order:

### Phase 1: Critical Fixes (Do First)
1. Fix seek bar control bug → See `@BUGS_AND_SOLUTIONS.md` #1
2. Add missing attribute initialization → See `@BUGS_AND_SOLUTIONS.md` #2
3. Implement filename sanitization → See `@BUGS_AND_SOLUTIONS.md` #3
4. Add resource cleanup on exit → See `@BUGS_AND_SOLUTIONS.md` #4

### Phase 2: Code Quality (Do Second)
5. Add docstrings to all classes/methods
6. Add type hints
7. Extract large methods into smaller functions
8. Add error handling where missing

### Phase 3: Feature Completion (Do Third)
9. Complete playlist download UI
10. Implement all visualizer modes
11. Add theme picker
12. Build media library features

### Phase 4: Refactoring (Do Last)
13. Split into modules (see `@ARCHITECTURE.md`)
14. Add unit tests
15. Create proper configuration system
16. Implement proper logging

---

## 🤖 AI Agent Guidelines

### When Fixing Bugs
1. **Read the bug report** in `@BUGS_AND_SOLUTIONS.md` first
2. **Explain your understanding** of the root cause
3. **Show the fix** with before/after code
4. **Test considerations**: Mention how to verify the fix
5. **Document the change**: Update relevant sections

### When Adding Features
1. **Check existing patterns** in `@CODE_EXAMPLES.md`
2. **Follow threading rules**: Never block main thread
3. **Match code style**: PEP 8, existing naming conventions
4. **Add comments**: Explain complex logic
5. **Consider GUI**: Tkinter-specific patterns

### When Refactoring
1. **Reference architecture guide**: `@ARCHITECTURE.md`
2. **Small incremental changes**: Don't rewrite everything
3. **Maintain functionality**: Keep existing features working
4. **Test after each change**: Run the application
5. **Ask before major restructuring**: Get user approval

### Communication Style
- **Be direct**: Clear explanations without fluff
- **Show code**: Concrete examples over abstract descriptions
- **Reference docs**: Point to specific sections in reference files
- **Explain trade-offs**: When multiple solutions exist
- **Ask when uncertain**: Don't guess about user preferences

---

## 📖 Additional Documentation

- **`@ARCHITECTURE.md`**: Detailed architectural patterns, recommended structure, threading models
- **`@BUGS_AND_SOLUTIONS.md`**: Complete bug list with root causes and code solutions
- **`@CODE_EXAMPLES.md`**: Good/bad code patterns, anti-patterns to avoid
- **`@CODE_REVIEW_NOTES.md`**: Original code review findings and recommendations
- **`@GEMINI.md`**: Gemini CLI specific instructions (if using Google's Gemini CLI)

---

## 🔄 Document Updates

**Last updated**: Based on comprehensive research of 10+ open-source Python video downloader projects and AGENTS.md standards

**Maintenance**: Update this file when:
- Project structure changes
- New critical bugs discovered
- Major features added
- Dependencies change
- Best practices evolve

---

*This file follows the AGENTS.md standard. Learn more at https://agents.md/*
