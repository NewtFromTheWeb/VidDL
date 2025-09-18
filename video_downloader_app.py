"""
A simple video downloader application with a graphical user interface built using Tkinter.
This application allows users to download videos from various websites using the yt-dlp library
and play them in an embedded player with playback controls.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.scrolledtext import ScrolledText
import yt_dlp
import threading
import os
import vlc
import time
import sys
import io
from PIL import Image, ImageTk
import urllib.request
import numpy as np
import librosa

class StdoutRedirector:
    """A class to redirect stdout or stderr to a Tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self, string):
        self.text_space.configure(state='normal')
        self.text_space.insert('end', string)
        self.text_space.see('end')
        self.text_space.configure(state='disabled')

    def flush(self):
        pass

class VideoDownloaderApp(tk.Tk):
    """
    The main application class for the Video Downloader.
    This class initializes the GUI and handles all application logic.
    """
    def __init__(self):
        """
        Initializes the main application window and its widgets.
        """
        super().__init__()

        self.title("Video Downloader")
        self.geometry("900x800")
        self.download_dir = None
        self.downloaded_file_path = None
        self.formats = []
        self.mp3_var = tk.BooleanVar()
        self.vlc_instance = vlc.Instance("--file-caching=2000")
        self.media_player = self.vlc_instance.media_player_new()
        self.is_playing = False
        self.is_paused = False
        self.thumbnail_photo = None
        self.log_viewer_visible = tk.BooleanVar(value=False)
        self.audio_data = None
        self.sample_rate = None
        self.is_visualizing = False
        self.visualizer_update_job = None

        # --- Style ---
        style = ttk.Style(self)
        style.theme_use('clam')

        # --- Main Layout ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Player and Metadata Notebook ---
        self.player_notebook = ttk.Notebook(self)
        self.player_notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.video_frame = ttk.Frame(self.player_notebook)
        self.visualizer_frame = ttk.Frame(self.player_notebook)
        self.player_notebook.add(self.video_frame, text="Player")
        self.player_notebook.add(self.visualizer_frame, text="Audio Visualizer")
        
        self.media_player.set_hwnd(self.video_frame.winfo_id())

        # --- Visualizer Canvas ---
        self.visualizer_canvas = tk.Canvas(self.visualizer_frame, bg='black')
        self.visualizer_canvas.pack(fill="both", expand=True)

        # --- Metadata Frame ---
        self.metadata_frame = ttk.LabelFrame(self, text="Video Information")
        self.metadata_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.metadata_frame.grid_columnconfigure(1, weight=1)

        self.thumbnail_label = ttk.Label(self.metadata_frame, text="Thumbnail will appear here.")
        self.thumbnail_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
        self.title_label = ttk.Label(self.metadata_frame, text="Title: ", wraplength=600, font=('TkDefaultFont', 10, 'bold'))
        self.title_label.grid(row=0, column=1, sticky="w", padx=5)
        self.duration_label = ttk.Label(self.metadata_frame, text="Duration: ")
        self.duration_label.grid(row=1, column=1, sticky="w", padx=5)

        # --- Player Controls Frame ---
        player_controls_frame = ttk.Frame(self)
        player_controls_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        player_controls_frame.grid_columnconfigure(1, weight=1)

        self.play_pause_button = ttk.Button(player_controls_frame, text="▶ Play", command=self.play_pause)
        self.play_pause_button.grid(row=0, column=0, padx=(0, 5))

        self.seek_slider = ttk.Scale(player_controls_frame, from_=0, to=1000, orient="horizontal", command=self.set_position)
        self.seek_slider.grid(row=0, column=1, sticky="ew", padx=5)
        self.seek_slider.bind("<ButtonPress-1>", lambda e: self.media_player.pause())
        self.seek_slider.bind("<ButtonRelease-1>", lambda e: self.play_pause(force_play=True))

        self.time_label = ttk.Label(player_controls_frame, text="00:00 / 00:00")
        self.time_label.grid(row=0, column=2, padx=5)

        self.volume_slider = ttk.Scale(player_controls_frame, from_=0, to=100, orient="horizontal", command=self.set_volume)
        self.volume_slider.set(100)
        self.volume_slider.grid(row=0, column=3, padx=5)
        
        # --- Control Panel Frame ---
        control_panel = ttk.LabelFrame(self, text="Control Panel")
        control_panel.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        control_panel.grid_columnconfigure(0, weight=1)

        # --- URL Frame ---
        url_frame = ttk.Frame(control_panel)
        url_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        url_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=(5,0))
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=(5, 5))

        # --- Formats Frame ---
        formats_frame = ttk.Frame(control_panel)
        formats_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        formats_frame.grid_columnconfigure(1, weight=1)
        self.fetch_button = ttk.Button(formats_frame, text="Fetch Formats", command=self.fetch_formats)
        self.fetch_button.grid(row=0, column=0, padx=(5,0))
        self.format_combo = ttk.Combobox(formats_frame, state='readonly')
        self.format_combo.grid(row=0, column=1, sticky="ew", padx=(5, 5))

        # --- Directory Selection ---
        dir_frame = ttk.Frame(control_panel)
        dir_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        dir_frame.grid_columnconfigure(0, weight=1)
        self.dir_label = ttk.Label(dir_frame, text="Download to: Not selected")
        self.dir_label.grid(row=0, column=0, sticky="ew", padx=(5,0))
        self.browse_button = ttk.Button(dir_frame, text="Browse", command=self.browse_directory)
        self.browse_button.grid(row=0, column=1, padx=(0,5))

        # --- Download Options ---
        options_frame = ttk.Frame(control_panel)
        options_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        self.mp3_check = ttk.Checkbutton(options_frame, text="Download as MP3", variable=self.mp3_var, command=self.toggle_format_combo)
        self.mp3_check.pack(side='left', padx=5)

        self.log_toggle_check = ttk.Checkbutton(options_frame, text="Show Log", variable=self.log_viewer_visible, command=self.toggle_log_viewer)
        self.log_toggle_check.pack(side='left', padx=5)

        self.download_button = ttk.Button(options_frame, text="Download", command=self.download_video)
        self.download_button.pack(side='right', padx=5)

        # --- Progress and Status ---
        status_frame = ttk.Frame(control_panel)
        status_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        status_frame.grid_columnconfigure(0, weight=1)
        self.progress_bar = ttk.Progressbar(status_frame, orient='horizontal', mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(5, 5))
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(5,0), padx=(5,5))

        # --- Log Viewer Frame (initially hidden) ---
        self.log_frame = ttk.Frame(self)
        self.log_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        self.log_frame.grid_remove() # Hide it initially
        log_text = ScrolledText(self.log_frame, height=10, state='disabled')
        log_text.pack(fill='both', expand=True)
        sys.stdout = StdoutRedirector(log_text)
        sys.stderr = StdoutRedirector(log_text)

    def toggle_log_viewer(self):
        if self.log_viewer_visible.get():
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()

    def fetch_formats(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Error: Please enter a URL first.")
            return
        self.status_label.config(text="Fetching formats...")
        self.fetch_button.config(state="disabled")
        self.format_combo['values'] = []
        self.formats = []
        thread = threading.Thread(target=self.fetch_formats_thread, args=(url,))
        thread.start()

    def fetch_formats_thread(self, url):
        try:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            # --- Update Metadata ---
            self.after(0, self.update_metadata, info)

            display_formats = []
            self.formats = []
            all_video_formats = [f for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height')]
            all_video_formats.sort(key=lambda f: f.get('height', 0), reverse=True)

            for f in all_video_formats:
                filesize = f.get('filesize') or f.get('filesize_approx')
                filesize_mb = f"{filesize / (1024*1024):.2f} MB" if filesize else "N/A"
                display_text = f"{f.get('height')}p - {f.get('ext')} ({filesize_mb})"
                self.formats.append({'text': display_text, 'id': f['format_id']})
                display_formats.append(display_text)

            if not self.formats:
                self.status_label.config(text="No suitable video formats found.")
            else:
                self.format_combo['values'] = display_formats
                self.format_combo.current(0)
                self.status_label.config(text="Formats loaded. Select quality and download.")
        except Exception as e:
            self.status_label.config(text=f"Error fetching formats: {str(e)}")
        finally:
            self.fetch_button.config(state="normal")

    def update_metadata(self, info):
        title = info.get('title', 'N/A')
        duration = info.get('duration', 0)
        thumbnail_url = info.get('thumbnail')

        self.title_label.config(text=f"Title: {title}")
        duration_str = time.strftime('%H:%M:%S', time.gmtime(duration)) if duration else "N/A"
        self.duration_label.config(text=f"Duration: {duration_str}")

        if thumbnail_url:
            thread = threading.Thread(target=self.load_thumbnail, args=(thumbnail_url,))
            thread.start()

    def load_thumbnail(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((160, 90))
            self.thumbnail_photo = ImageTk.PhotoImage(img)
            self.thumbnail_label.config(image=self.thumbnail_photo)
        except Exception as e:
            self.thumbnail_label.config(text="Thumbnail\nfailed to load")
            print(f"Error loading thumbnail: {e}")

    def toggle_format_combo(self):
        if self.mp3_var.get():
            self.format_combo.config(state='disabled')
        else:
            self.format_combo.config(state='readonly')

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_dir = directory
            self.dir_label.config(text=f"Download to: {directory}")

    def download_video(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Error: Please enter a URL.")
            return
        if not self.download_dir:
            self.status_label.config(text="Error: Please select a download directory.")
            return
        if not self.formats and not self.mp3_var.get():
            self.status_label.config(text="Error: Please fetch formats first.")
            return

        self.download_button.config(state="disabled")
        self.fetch_button.config(state="disabled")
        self.progress_bar['value'] = 0
        
        selected_format = None
        if not self.mp3_var.get():
            selected_format_text = self.format_combo.get()
            for f in self.formats:
                if f['text'] == selected_format_text:
                    selected_format = f
                    break
        
        thread = threading.Thread(target=self.download_thread, args=(url, self.download_dir, self.mp3_var.get(), selected_format))
        thread.start()

    def download_thread(self, url, download_path, is_mp3, selected_format):
        try:
            ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
            if not os.path.exists(ffmpeg_path):
                raise FileNotFoundError("ffmpeg.exe not found in application folder.")

            output_template = os.path.join(download_path, '%(title)s.%(ext)s')

            if is_mp3:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'progress_hooks': [self.progress_hook],
                    'ffmpeg_location': ffmpeg_path,
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                }
            else:
                format_id = selected_format['id']
                ydl_opts = {
                    'format': f"{format_id}+bestaudio[ext=m4a]/bestaudio",
                    'outtmpl': output_template,
                    'progress_hooks': [self.progress_hook],
                    'ffmpeg_location': ffmpeg_path,
                    'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
                    'merge_output_format': 'mp4',
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                base, _ = os.path.splitext(ydl.prepare_filename(info))
                if is_mp3:
                    self.downloaded_file_path = base + '.mp3'
                else:
                    self.downloaded_file_path = base + '.mp4'
                ydl.download([url])

            self.status_label.config(text="Download Complete. Ready to play.")
            if self.downloaded_file_path:
                self.after(0, self.play_media)

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            print(e)
        finally:
            self.download_button.config(state="normal")
            self.fetch_button.config(state="normal")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percentage = (d['downloaded_bytes'] / total_bytes) * 100
                self.progress_bar['value'] = percentage
                self.status_label.config(text=f"Downloading... {percentage:.2f}%")
                self.update_idletasks()
        elif d['status'] == 'finished':
            self.status_label.config(text="Finalizing file...")
            self.progress_bar['value'] = 100

    def play_media(self):
        # Stop any currently running visualizer loop
        if self.visualizer_update_job:
            self.after_cancel(self.visualizer_update_job)
            self.visualizer_update_job = None

        if self.downloaded_file_path and os.path.exists(self.downloaded_file_path):
            self.is_visualizing = False # Reset visualizer flag
            media = self.vlc_instance.media_new(self.downloaded_file_path)
            self.media_player.set_media(media)
            
            if self.mp3_var.get():
                self.player_notebook.select(self.visualizer_frame)
                thread = threading.Thread(target=self.load_audio_data)
                thread.start()
                self.update_visualizer_ui() # Start the fast loop for the visualizer
            else:
                self.player_notebook.select(self.video_frame)

            self.play_pause(force_play=True)
        else:
            self.status_label.config(text="Error: Downloaded file not found.")

    def load_audio_data(self):
        try:
            self.status_label.config(text="Loading audio for visualizer...")
            self.audio_data, self.sample_rate = librosa.load(self.downloaded_file_path, sr=None)
            self.is_visualizing = True
            self.status_label.config(text="Playing audio.")
        except Exception as e:
            print(f"Error loading audio data: {e}")
            self.status_label.config(text="Error: Could not load audio for visualizer.")

    def visualize_audio(self):
        if not self.is_visualizing or not self.media_player.is_playing() or self.audio_data is None:
            return

        # Get current time in the audio
        current_time_ms = self.media_player.get_time()
        current_sample = int((current_time_ms / 1000.0) * self.sample_rate)

        # Define a chunk size for FFT
        chunk_size = 2048
        if current_sample + chunk_size > len(self.audio_data):
            return

        # Get the audio chunk and perform FFT
        audio_chunk = self.audio_data[current_sample : current_sample + chunk_size]
        fft_result = np.fft.fft(audio_chunk)
        fft_freq = np.fft.fftfreq(len(fft_result), 1/self.sample_rate)
        
        # We only need the positive frequencies
        fft_result = np.abs(fft_result[:len(fft_result)//2])
        fft_freq = fft_freq[:len(fft_freq)//2]

        # Group frequencies into bands for visualization
        num_bands = 32
        band_width = len(fft_result) // num_bands
        bands = [np.mean(fft_result[i*band_width:(i+1)*band_width]) for i in range(num_bands)]
        
        # --- Drawing on Canvas ---
        canvas = self.visualizer_canvas
        canvas.delete("all")
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        bar_width = canvas_width / num_bands

        # Normalize and scale bands
        max_band = max(bands) if max(bands) > 0 else 1.0
        scaled_bands = [b / max_band for b in bands]

        for i, height in enumerate(scaled_bands):
            x0 = i * bar_width
            y0 = canvas_height
            x1 = (i + 1) * bar_width
            y1 = canvas_height - (height * canvas_height * 0.9)
            
            # Gradient color
            color_intensity = int(height * 255)
            color = f'#{0:02x}{color_intensity:02x}{255-color_intensity:02x}' # Blue to Green gradient
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline=color)

    def play_pause(self, force_play=False):
        if self.media_player.is_playing() and not force_play:
            self.media_player.pause()
            self.play_pause_button.config(text="▶ Play")
            self.is_paused = True
        else:
            if self.media_player.play() == -1:
                self.status_label.config(text="Error: Cannot play media.")
                return
            self.play_pause_button.config(text="❚❚ Pause")
            self.is_paused = False

    def set_volume(self, volume):
        self.media_player.audio_set_volume(int(float(volume)))

    def set_position(self, pos):
        if self.media_player.is_seekable():
            self.media_player.set_position(float(pos) / 1000)


    def update_visualizer_ui(self):
        """Fast update loop for the audio visualizer animation."""
        if self.is_visualizing:
            self.visualize_audio()
        self.visualizer_update_job = self.after(50, self.update_visualizer_ui)


if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()