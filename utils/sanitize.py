import re
import unicodedata

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename for filesystem compatibility.
    
    Handles illegal characters, unicode normalization, and length limits.
    Based on patterns from Tartube, ytdlp-gui, and yt-dlp-gui projects.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length (default 200)
        
    Returns:
        Safe filename for any filesystem
        
    Examples:
        >>> sanitize_filename("Video: Cool Stuff?")
        'Video- Cool Stuff'
        >>> sanitize_filename("Tutorial 1/3")
        'Tutorial 1-3'
    """
    # Normalize unicode characters (handles accents, emoji, etc.)
    filename = unicodedata.normalize('NFKD', filename)
    
    # Convert to ASCII, replacing non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Replace illegal characters with safe alternatives
    replacements = {
        '/': '-',   # Path separator (Unix)
        '\\': '-',  # Path separator (Windows)
        ':': '-',   # Drive separator (Windows)
        '*': '',    # Wildcard
        '?': '',    # Wildcard
        '"': "'",   # Quote to apostrophe
        '<': '',    # Redirect
        '>': '',    # Redirect
        '|': '-',   # Pipe
    }
    
    for illegal_char, replacement in replacements.items():
        filename = filename.replace(illegal_char, replacement)
    
    # Collapse multiple spaces into one
    filename = re.sub(r'\s+', ' ', filename)
    
    # Remove leading/trailing problematic characters
    filename = filename.strip(' .-')
    
    # Enforce length limit (preserve extension if possible)
    if len(filename) > max_length:
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}"
        else:
            filename = filename[:max_length]
    
    # Ensure we don't return empty string
    if not filename:
        filename = "untitled"
    
    return filename
