# VidDL - Gemini CLI Context

> **For Google Gemini CLI users only**. If using Claude Code or other AI tools, see `@AGENT.md` instead.

## Quick Start

This file provides persistent context for Google's Gemini CLI when working on the VidDL video downloader project.

**Key commands**:
- `/memory show` - View all loaded context
- `/plan <task>` - Create implementation plan
- `/implement` - Execute approved plan
- `/help` - Show available commands

**Core documentation**:
- `@AGENT.md` - Complete project instructions (also useful for Gemini)
- `@ARCHITECTURE.md` - Architectural patterns and structure
- `@BUGS_AND_SOLUTIONS.md` - Known issues with solutions
- `@CODE_EXAMPLES.md` - Code patterns and anti-patterns

---

## Project Identity

**VidDL** is a desktop video/audio downloader with embedded playback. Downloads from YouTube, TikTok, Reddit, and any yt-dlp-supported site. Features VLC player integration, audio visualizations, and playlist batch downloading.

**Primary file**: `video_downloader_app.py` (900+ lines, monolithic)
**Tech stack**: Python 3 + Tkinter + yt-dlp + python-vlc + librosa + numpy
**Critical dependency**: `ffmpeg.exe` in project root

---

## Operational Modes

<PROTOCOL:READ_ONLY>
### Read-Only Mode (Default)
**When exploring or analyzing code**:
- ✅ Read any project file
- ✅ Analyze code structure
- ✅ Search for patterns
- ✅ Explain functionality
- ✅ Answer questions
- ❌ NO modifications allowed
- ❌ NO file creation
- ❌ NO deletions

**Purpose**: Safe exploration without risk of unwanted changes
</PROTOCOL:READ_ONLY>

<PROTOCOL:PLAN>
### Plan Mode
**When user asks to create a plan**:

1. **Strictly Read-Only**: Only inspect files, never modify
2. **Understand the request**: Clarify requirements if ambiguous
3. **Analyze current state**: Review relevant code sections
4. **Identify constraints**: Note dependencies, patterns, limitations
5. **Create detailed plan**: 
   - Break into discrete steps
   - List files to modify/create
   - Explain reasoning for each step
   - Note potential risks
   - Estimate complexity
6. **Present for approval**: Wait for explicit user confirmation
7. **NEVER implement**: Planning phase only

**Example plan format**:
```
## Plan: Fix Seek Bar Control Bug

### Analysis
- Current issue: Seek slider events conflict with volume slider
- Root cause: Both use Scale widgets with overlapping command bindings
- Affected files: video_downloader_app.py (lines 268-274)

### Implementation Steps
1. Separate seek control logic from volume control
   - Remove `command` parameter from seek slider
   - Use ButtonPress/Release events ONLY for seek
   - Keep volume slider using `command` parameter

2. Implement VLC polling pattern
   - Create `update_seek_slider()` method
   - Use `self.after(100, update_seek_slider)` for polling
   - Update position only when NOT manually seeking

3. Add state management
   - Ensure `self.is_seeking` flag prevents automatic updates
   - Clear separation between manual and automatic position updates

### Files to modify
- video_downloader_app.py: Lines 268-290 (control initialization)
- video_downloader_app.py: Lines 565-605 (seek methods)

### Risks
- Low: Well-tested pattern from production projects

### Testing
- Manual: Drag seek bar, verify position changes
- Manual: Adjust volume, verify no position change
- Manual: Play video, verify automatic position updates

Ready to implement? [Awaiting approval]
```
</PROTOCOL:PLAN>

<PROTOCOL:IMPLEMENT>
### Implement Mode
**When executing an approved plan**:

1. **Verify approval**: Confirm plan received explicit user approval
2. **Execute systematically**: Follow plan steps in order
3. **Show progress**: Explain each modification as you make it
4. **Handle errors gracefully**: If issues arise, stop and report
5. **Test after changes**: Suggest verification steps
6. **Document changes**: Update comments, docstrings as needed

**Modification rules**:
- ✅ Modify existing Python files to fix bugs
- ✅ Add new Python files for refactoring
- ✅ Create documentation files
- ✅ Add comments and docstrings
- ❌ Never delete files without explicit permission
- ❌ Never modify binaries (ffmpeg.exe)
- ❌ Never change .git directory

**After implementation**:
```
## Implementation Complete: <Task Name>

### Changes made
- File: video_downloader_app.py
  - Modified lines 268-274: Separated seek control initialization
  - Added method `update_seek_slider()`: VLC polling pattern
  - Updated lines 565-580: New seek event handlers

### Testing recommendations
1. Run application: `python video_downloader_app.py`
2. Load a video
3. Test seek bar: Drag to different positions
4. Test volume: Adjust volume slider
5. Verify: Seek bar updates automatically during playback

### Next steps
- Test the changes
- Report any issues
- Move to next bug fix
```
</PROTOCOL:IMPLEMENT>

<PROTOCOL:DEBUG>
### Debug Mode
**When investigating errors or unexpected behavior**:

1. **Gather information**: 
   - Error messages
   - Stack traces
   - User description
   - Expected vs actual behavior

2. **Analyze systematically**:
   - Review error location in code
   - Check related functionality
   - Search for similar patterns
   - Consider threading issues (common in this app)

3. **Form hypotheses**: List possible causes ranked by likelihood

4. **Suggest verification steps**: How to confirm each hypothesis

5. **Propose solutions**: With code examples

**Common debugging areas for this project**:
- **Threading issues**: GUI updates from worker threads
- **VLC integration**: Event handling, resource cleanup
- **File operations**: Path handling, filename sanitization
- **yt-dlp**: Network errors, format selection

See `@BUGS_AND_SOLUTIONS.md` for known issues and patterns
</PROTOCOL:DEBUG>

---

## Code Conventions

### Python Style
- **PEP 8 compliant**: Standard Python formatting
- **Line length**: 100 characters (acceptable for Tkinter code)
- **Indentation**: 4 spaces, never tabs
- **Type hints**: Gradually add to new/modified code
- **Docstrings**: Google style format

### Tkinter-Specific
**CRITICAL RULES**:
1. **Never block main thread**: All yt-dlp operations in threads
2. **Always use daemon threads**: `threading.Thread(..., daemon=True)`
3. **GUI updates from threads**: Only via `self.after(0, callback)`
4. **Resource cleanup**: Always stop media player and cancel timers

**Example patterns** (see `@CODE_EXAMPLES.md` for full examples):
```python
# ✅ CORRECT: Non-blocking download
def download_video(self):
    thread = threading.Thread(target=self._download_worker, daemon=True)
    thread.start()

# ✅ CORRECT: Thread-safe GUI update
def _download_worker(self):
    result = download_data()
    self.after(0, lambda: self.status_label.config(text="Done"))
```

### Naming Conventions
- Classes: `VideoDownloaderApp` (PascalCase)
- Methods: `fetch_url_info` (snake_case)
- Private: `_download_worker` (leading underscore)
- Constants: `MAX_RETRIES` (UPPER_SNAKE_CASE)

---

## Priority Tasks

**Refer to `@BUGS_AND_SOLUTIONS.md` for detailed information on each bug**

### Immediate (P0)
1. **Fix seek bar control bug** - HIGH IMPACT
   - Current: Seek bar acts as volume control
   - Solution: VLC polling pattern
   - Impact: Core playback functionality broken

2. **Add missing initialization** - HIGH IMPACT
   - Current: `is_playing_from_library` AttributeError
   - Solution: Add to `__init__`
   - Impact: Library playback crashes

### High Priority (P1)
3. **Filename sanitization** - MEDIUM IMPACT
   - Current: Special characters cause download failures
   - Solution: Unicode normalization + character replacement
   - Impact: Downloads fail for ~10% of videos

4. **Resource cleanup** - MEDIUM IMPACT
   - Current: VLC and threads persist after close
   - Solution: `on_closing()` method
   - Impact: Memory leaks, hanging processes

### Future Work (P2)
5. Complete playlist download UI
6. Implement all visualizer modes
7. Add theme picker
8. Refactor into modules (see `@ARCHITECTURE.md`)

---

## File Operations

### Safe to modify
```
video_downloader_app.py   - Main application file
*.md                      - All documentation files
```

### Read-only (ask before modifying)
```
ffmpeg.exe               - Binary, should never change
.git/                    - Version control, Git manages this
```

### Does not exist yet (safe to create)
```
requirements.txt         - Python dependencies
tests/                   - Test directory
config.py               - Configuration
```

---

## Common Tasks

### When fixing a bug
1. Check `@BUGS_AND_SOLUTIONS.md` for known issues
2. Explain your understanding of root cause
3. Reference similar patterns in `@CODE_EXAMPLES.md`
4. Show before/after code
5. Mention testing approach

### When adding a feature
1. Check user's roadmap in original GEMINI.md (see historical version)
2. Follow existing code style and patterns
3. Respect threading rules (never block GUI)
4. Add comments for complex logic
5. Update documentation

### When refactoring
1. Reference `@ARCHITECTURE.md` for recommended structure
2. Make small, incremental changes
3. Test after each change
4. Don't rewrite everything at once
5. Ask before major structural changes

---

## Tool Configuration

### Available Gemini CLI tools
**Default tools** (no additional configuration needed):
- File reading/writing
- Web search (for documentation lookup)
- Code analysis
- Reasoning

**Recommended additional tools** (configure in settings.json):
- GitHub integration (for issue tracking)
- Python REPL (for testing code snippets)

### MCP Servers (Optional)
Consider connecting these Model Context Protocol servers:
- `@modelcontextprotocol/server-filesystem` - Enhanced file operations
- `@modelcontextprotocol/server-github` - GitHub integration
- `@modelcontextprotocol/server-memory` - Persistent memory

---

## Reference Documentation

### Core files (read these first)
- **`@AGENT.md`**: Complete project instructions, works for any AI tool
- **`@ARCHITECTURE.md`**: Architectural patterns, recommended structure
- **`@BUGS_AND_SOLUTIONS.md`**: All known bugs with detailed solutions
- **`@CODE_EXAMPLES.md`**: Good/bad patterns, anti-patterns

### Supporting files
- **`@CODE_REVIEW_NOTES.md`**: Original code review findings
- **`README.md`**: User-facing project description

### Research basis
This documentation structure is based on research of:
- 10+ production Python video downloader projects
- AGENTS.md standard (20,000+ projects)
- Gemini CLI best practices
- Threading patterns from Tartube, ytdlp-gui, and others

---

## Context Management

### View loaded context
```
/memory show
```
This displays all GEMINI.md files loaded from:
- This directory
- Parent directories (if in subdirectory)
- Global `~/.gemini/GEMINI.md` (if configured)

### If context seems wrong
1. Check you're in the project root directory
2. Run `/memory show` to see what's loaded
3. Verify GEMINI.md hasn't been corrupted
4. Reference files explicitly with `@filename.md`

### Keep context lean
- Main instructions here (this file)
- Detailed information in linked files
- Prevents context overload
- Enables focused, efficient assistance

---

## Emergency Contacts

### If something goes wrong
1. **Stop immediately**: Don't make more changes
2. **Show user**: Explain what happened
3. **Check git status**: See what files changed
4. **Offer solutions**: Rollback or fix options

### If confused about requirements
1. **Ask user**: Don't guess
2. **Reference docs**: Point to relevant section
3. **Suggest alternatives**: If multiple approaches exist

### If hitting token limits
1. **Be concise**: Cut unnecessary words
2. **Use references**: Point to docs instead of repeating
3. **Focus narrowly**: One task at a time

---

## Gemini CLI Workflow Example

**Typical session flow**:

```
# User starts session
$ gemini chat

# Gemini loads this file automatically

# User: "Fix the seek bar bug"
> /plan Fix the seek bar control bug
[Gemini enters PLAN mode, creates detailed plan]

# User: "Looks good, implement it"
> /implement
[Gemini enters IMPLEMENT mode, makes changes]

# User: "Thanks! Now let's work on filename sanitization"
> /plan Add filename sanitization
[Process repeats]
```

**Best practices**:
- Use `/plan` before making changes
- Review plans before approving
- Test after each implementation
- Keep changes small and focused

---

## Update History

**Current version**: Based on comprehensive research of production video downloaders
**Last updated**: October 2025
**Research sources**: Tartube, ytdlp-gui, yt-dlp-gui, and AGENTS.md standard

**Update this file when**:
- Project structure changes significantly
- New critical bugs discovered
- Major features completed
- Best practices evolve

---

*For additional context, always reference `@AGENT.md`, `@ARCHITECTURE.md`, `@BUGS_AND_SOLUTIONS.md`, and `@CODE_EXAMPLES.md`*
