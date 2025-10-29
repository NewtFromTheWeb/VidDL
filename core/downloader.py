import os
import subprocess
import threading

class Downloader:
    def __init__(self, download_complete_callback=None):
        self.download_complete_callback = download_complete_callback

    def download(self, videos, download_path, is_mp3, is_playlist):
        thread = threading.Thread(target=self._download_thread, args=(videos, download_path, is_mp3, is_playlist), daemon=True)
        thread.start()

    def _download_thread(self, videos, download_path, is_mp3, is_playlist):
        for video_info in videos:
            video_url = video_info.get('url') or video_info.get('webpage_url')

            if is_playlist:
                output_template = os.path.join(download_path, '%(uploader)s', '%(playlist_title)s', '%(title)s.%(ext)s')
            else:
                output_template = os.path.join(download_path, '%(title)s.%(ext)s')

            command = [
                'yt-dlp',
                '--ffmpeg-location', os.path.join(os.getcwd(), "ffmpeg.exe"),
                '--restrict-filenames',
                '-o', output_template,
            ]

            if is_mp3:
                command.extend(['-x', '--audio-format', 'mp3'])
            
            command.append(video_url)

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"Error downloading {video_url}: {stderr.decode('utf-8', errors='ignore')}")
            else:
                print(f"Finished downloading {video_url}")

        if self.download_complete_callback:
            self.download_complete_callback()
