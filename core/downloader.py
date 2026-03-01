import os
import threading
import yt_dlp

class Downloader:
    """
    Handles video downloads using the yt-dlp Python library.
    
    This class wraps the yt-dlp functionality and provides a threaded 
    interface for downloading videos without blocking the GUI.
    """
    def __init__(self, download_complete_callback=None, progress_callback=None):
        """
        Initializes the Downloader.
        
        Args:
            download_complete_callback (callable, optional): Called when all downloads are finished.
            progress_callback (callable, optional): Called with progress updates (dict).
        """
        self.download_complete_callback = download_complete_callback
        self.progress_callback = progress_callback
        self.is_cancelled = False

    def download(self, videos, download_path, is_mp3, is_playlist, format_id=None, write_subs=False):
        """
        Starts the download process in a separate thread.
        
        Args:
            videos (list): List of video information dictionaries.
            download_path (str): The directory to save the downloads to.
            is_mp3 (bool): Whether to download as audio only (MP3).
            is_playlist (bool): Whether the input is a playlist.
            format_id (str, optional): The format ID to use.
            write_subs (bool): Whether to download subtitle files.
        """
        self.is_cancelled = False
        thread = threading.Thread(
            target=self._download_thread, 
            args=(videos, download_path, is_mp3, is_playlist, format_id, write_subs), 
            daemon=True
        )
        thread.start()

    def _progress_hook(self, d):
        """Internal hook for yt-dlp to report progress."""
        if self.progress_callback:
            self.progress_callback(d)
        
        if self.is_cancelled:
            raise Exception("Download cancelled by user")

    def _download_thread(self, videos, download_path, is_mp3, is_playlist, format_id, write_subs):
        """Thread worker for downloading videos."""
        ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
        
        for video_info in videos:
            if self.is_cancelled:
                break
                
            video_url = video_info.get('url') or video_info.get('webpage_url')
            if not video_url:
                continue

            # Define output template
            if is_playlist:
                output_template = os.path.join(download_path, '%(uploader)s', '%(playlist_title)s', '%(title)s.%(ext)s')
            else:
                output_template = os.path.join(download_path, '%(title)s.%(ext)s')

            # Configure robust yt-dlp options
            ydl_opts = {
                'outtmpl': output_template,
                'ffmpeg_location': ffmpeg_path,
                'restrictfilenames': True,
                'progress_hooks': [self._progress_hook],
                'quiet': True,
                'no_warnings': True,
                # Resilience options to prevent stalls
                'retries': 20,
                'fragment_retries': 20,
                'socket_timeout': 30,
                'continuedl': True,
                'file_access_retries': 5,
            }

            # Subtitle options
            if write_subs:
                ydl_opts.update({
                    'writesubtitles': True,
                    'allsubs': True,
                    'writeautomaticsub': True,
                    'subtitlesformat': 'srt/vtt',
                })

            if is_mp3:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                # Use user-selected format ID if provided, otherwise default to best
                if format_id:
                    # If user chose a specific quality, we combine with bestaudio if it doesn't have it
                    if '+' not in format_id and 'best' not in format_id:
                        ydl_opts['format'] = f"{format_id}+bestaudio/best"
                    else:
                        ydl_opts['format'] = format_id
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                    
                ydl_opts['merge_output_format'] = 'mp4'

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                print(f"Finished downloading {video_url}")
            except Exception as e:
                if "cancelled" in str(e).lower():
                    print("Download cancelled.")
                else:
                    print(f"Error downloading {video_url}: {str(e)}")

        if self.download_complete_callback:
            self.download_complete_callback()

    def cancel(self):
        """Cancels any ongoing downloads."""
        self.is_cancelled = True
