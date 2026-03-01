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
import json
import subprocess
from PIL import Image, ImageTk
import urllib.request
import numpy as np
import librosa
import random
from core.downloader import Downloader

class ChecklistTreeview(ttk.Treeview):
    """A Treeview widget with checkboxes for each item."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.tag_configure("checked", foreground="blue")
        self.tag_configure("unchecked", foreground="black")
        self.bind("<Button-1>", self.toggle_checkbox, True)

    def insert(self, parent, index, **kwargs):
        text = kwargs.pop("text", "")
        kwargs["text"] = f"☐ {text}"
        iid = super().insert(parent, index, **kwargs)
        self.item(iid, tags=("unchecked",))
        return iid

    def toggle_checkbox(self, event):
        row_id = self.identify_row(event.y)
        if not row_id:
            return

        tags = self.item(row_id, "tags")
        text = self.item(row_id, "text")

        if "checked" in tags:
            self.item(row_id, tags=("unchecked",), text=text.replace("☑", "☐"))
        else:
            self.item(row_id, tags=("checked",), text=text.replace("☐", "☑"))
        return "break"

class HierarchicalChecklistTreeview(ChecklistTreeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Button-1>", self.toggle_checkbox, True)

    def toggle_checkbox(self, event):
        row_id = self.identify_row(event.y)
        if not row_id:
            return

        # Toggle the clicked item
        super().toggle_checkbox(event)

        # If a parent is checked, check all its children
        children = self.get_children(row_id)
        if children:
            tags = self.item(row_id, "tags")
            if "checked" in tags:
                for child in children:
                    self.item(child, tags=("checked",), text=self.item(child, "text").replace("☐", "☑"))
            else:
                for child in children:
                    self.item(child, tags=("unchecked",), text=self.item(child, "text").replace("☑", "☐"))
        
        return "break"

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

        self.title("VidDL - Advanced Video Downloader")
        self.geometry("1100x850")
        self.minsize(1000, 750) # Prevents shrinking too much
        self.download_dir = None
        self.downloaded_file_path = None
        self.formats = []
        self.mp3_var = tk.BooleanVar()
        self.is_playlist = False
        self.subtitle_var = tk.BooleanVar(value=False)
        self.vlc_instance = vlc.Instance("--file-caching=3000 --network-caching=3000 --avcodec-hw=none --no-video-title-show")
        self.media_player = self.vlc_instance.media_player_new()
        self.is_playing = False
        self.is_paused = False
        self.thumbnail_photo = None
        self.log_viewer_visible = tk.BooleanVar(value=False)
        self.audio_data = None
        self.sample_rate = None
        self.is_visualizing = False
        self.visualizer_update_job = None
        self.playlist_videos = []
        self.is_playlist = False
        self.is_shuffling = False
        self.is_repeating = False
        self.is_seeking = False
        self.is_playing_from_library = False
        self.seek_var = tk.DoubleVar()
        self.volume_var = tk.DoubleVar()
        self.last_progress_update_time = 0.0
        self.visualizer_update_job = None
        self.beat_frames = None
        self._play_media_called = False

        # --- Style ---
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TCheckbutton", background=self.style.lookup('TFrame', 'background'))

        # --- Main Layout ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3) # Give more weight to the right pane
        self.grid_columnconfigure(0, weight=1)

        # --- Left Pane (Library) ---
        library_pane = ttk.LabelFrame(self, text="Media Library")
        library_pane.grid(row=0, column=0, sticky="nsew", padx=(10,0), pady=10)
        library_pane.grid_rowconfigure(0, weight=1)
        library_pane.grid_columnconfigure(0, weight=1)

        self.library_tree = ttk.Treeview(library_pane)
        self.library_tree.grid(row=0, column=0, sticky="nsew")
        self.library_tree.bind("<<TreeviewSelect>>", self.on_library_select)

        library_button_frame = ttk.Frame(library_pane)
        library_button_frame.grid(row=1, column=0, sticky="ew")
        
        self.browse_computer_button = ttk.Button(library_button_frame, text="Browse Computer", command=self.browse_computer)
        self.browse_computer_button.pack(side="left", fill="x", expand=True)
        
        self.populate_library_button = ttk.Button(library_button_frame, text="Refresh Downloads", command=self.populate_library)
        self.populate_library_button.pack(side="left", fill="x", expand=True)


        # --- Right Pane (Main Content) ---
        right_pane = ttk.Frame(self)
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)
        right_pane.grid_rowconfigure(0, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)

        # --- Top Panes (Player and Metadata) ---
        top_pane = ttk.Frame(right_pane)
        top_pane.grid(row=0, column=0, sticky="nsew")
        top_pane.grid_rowconfigure(0, weight=1)
        top_pane.grid_columnconfigure(0, weight=1)

        # --- Player and Visualizer Notebook ---
        self.player_notebook = ttk.Notebook(top_pane)
        self.player_notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Ensure notebook itself can expand
        top_pane.grid_rowconfigure(0, weight=1)
        top_pane.grid_columnconfigure(0, weight=1)

        self.video_frame = ttk.Frame(self.player_notebook)
        self.video_frame.pack(fill="both", expand=True)
        # Give video frame a minimum size to prevent shrinking to zero
        self.video_frame.config(width=800, height=450)
        
        self.visualizer_frame = ttk.Frame(self.player_notebook)
        self.visualizer_frame.pack(fill="both", expand=True)
        
        self.player_notebook.add(self.video_frame, text="Player")
        self.player_notebook.add(self.visualizer_frame, text="Audio Visualizer")
        self.player_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        

        event_manager = self.media_player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.media_ended)

        # --- Visualizer Canvas ---
        self.visualizer_canvas = tk.Canvas(self.visualizer_frame, bg='black')
        self.visualizer_canvas.pack(fill="both", expand=True)

        # --- Metadata Frame ---
        self.metadata_frame = ttk.LabelFrame(top_pane, text="Video Information")
        self.metadata_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.metadata_frame.grid_columnconfigure(1, weight=1)

        self.thumbnail_label = ttk.Label(self.metadata_frame, text="Thumbnail will appear here.")
        self.thumbnail_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
        self.title_label = ttk.Label(self.metadata_frame, text="Title: ", wraplength=700, font=('TkDefaultFont', 10, 'bold'))
        self.title_label.grid(row=0, column=1, sticky="w", padx=5)
        self.duration_label = ttk.Label(self.metadata_frame, text="Duration: ")
        self.duration_label.grid(row=1, column=1, sticky="w", padx=5)

        # --- Dynamic Frame for Playlist and Log ---
        dynamic_frame = ttk.Frame(right_pane)
        dynamic_frame.grid(row=2, column=0, sticky='nsew')
        dynamic_frame.grid_columnconfigure(0, weight=1)

        # --- Unified Controls Frame ---
        controls_frame = ttk.Frame(right_pane)
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))
        controls_frame.grid_columnconfigure(1, weight=1)

        # --- Row 0: URL and Fetch ---
        url_fetch_frame = ttk.Frame(controls_frame)
        url_fetch_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        url_fetch_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(url_fetch_frame, text="URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(url_fetch_frame)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.fetch_button = ttk.Button(url_fetch_frame, text="Fetch Info", command=self.fetch_url_info)
        self.fetch_button.grid(row=0, column=2)

        # --- Row 1: Player Controls ---
        player_controls_frame = ttk.Frame(controls_frame)
        player_controls_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        player_controls_frame.grid_columnconfigure(3, weight=1)

        self.previous_button = ttk.Button(player_controls_frame, text="<< Previous", command=self.play_previous)
        self.previous_button.grid(row=0, column=0, padx=(0, 5))

        self.play_pause_button = ttk.Button(player_controls_frame, text="▶ Play", command=self.play_pause)
        self.play_pause_button.grid(row=0, column=1, padx=(0, 5))

        self.next_button = ttk.Button(player_controls_frame, text="Next >>", command=self.play_next)
        self.next_button.grid(row=0, column=2, padx=(0, 10))

        # Shuffle and Repeat (using tk.Button for manual relief toggle)
        self.shuffle_button = tk.Button(player_controls_frame, text="🔀", command=self.toggle_shuffle)
        self.shuffle_button.grid(row=0, column=3, padx=5)
        
        self.repeat_button = tk.Button(player_controls_frame, text="🔁", command=self.toggle_repeat)
        self.repeat_button.grid(row=0, column=4, padx=5)

        self.seek_slider = ttk.Scale(player_controls_frame, from_=0, to=1000000, orient="horizontal", variable=self.seek_var, command=None)
        self.seek_slider.grid(row=0, column=5, sticky="ew", padx=5)
        self.seek_slider.grid_rowconfigure(0, weight=1)
        player_controls_frame.grid_columnconfigure(5, weight=1)
        self.seek_slider.bind("<ButtonPress-1>", self.on_seek_start)
        self.seek_slider.bind("<ButtonRelease-1>", self.on_seek_end)
        self.seek_slider.bind("<B1-Motion>", self.on_seek_motion)

        self.time_label = ttk.Label(player_controls_frame, text="00:00 / 00:00")
        self.time_label.grid(row=0, column=6, padx=5)

        self.volume_slider = ttk.Scale(player_controls_frame, from_=0, to=100, orient="horizontal", variable=self.volume_var, command=lambda v: self.set_volume())
        self.volume_var.set(100)
        self.volume_slider.grid(row=0, column=7, padx=(5, 0))

        # --- Row 2: Download Options ---
        download_options_frame = ttk.Frame(controls_frame)
        download_options_frame.grid(row=2, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        download_options_frame.grid_columnconfigure(0, weight=1)

        self.format_combo = ttk.Combobox(download_options_frame, state='readonly', width=40)
        self.format_combo.grid(row=0, column=0, sticky="ew", padx=(0,5))

        self.mp3_check = ttk.Checkbutton(download_options_frame, text="Download as MP3", variable=self.mp3_var, command=self.toggle_format_combo)
        self.mp3_check.grid(row=0, column=1, padx=5)

        self.subtitle_check = ttk.Checkbutton(download_options_frame, text="Subtitles", variable=self.subtitle_var)
        self.subtitle_check.grid(row=0, column=2, padx=5)

        self.log_toggle_check = ttk.Checkbutton(download_options_frame, text="Show Log", variable=self.log_viewer_visible, command=self.toggle_log_viewer)
        self.log_toggle_check.grid(row=0, column=3, padx=5)

        self.visualizer_style = tk.StringVar(value='Bar')
        self.visualizer_combo = ttk.Combobox(download_options_frame, textvariable=self.visualizer_style, state='readonly', width=15)
        self.visualizer_combo['values'] = ['Bar', 'Heartbeat', 'Spectrum', 'Oscilloscope', '3D']
        self.visualizer_combo.grid(row=0, column=4, padx=5)

        self.theme_style = tk.StringVar(value="Cyberpunk")
        self.theme_combo = ttk.Combobox(download_options_frame, textvariable=self.theme_style, state='readonly', width=15)
        self.theme_combo['values'] = ['Cyberpunk', 'Hacker', 'Vaporwave', 'Modern Dark']
        self.theme_combo.grid(row=0, column=6, padx=5)
        self.theme_combo.bind('<<ComboboxSelected>>', self.change_theme)
        self.after(500, self.change_theme) # Apply default theme after a short delay

        self.download_button = ttk.Button(download_options_frame, text="Download", command=self.download_video)
        self.download_button.grid(row=0, column=5, padx=5)

        # --- Row 3: Directory and Progress ---
        dir_progress_frame = ttk.Frame(controls_frame)
        dir_progress_frame.grid(row=3, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        dir_progress_frame.grid_columnconfigure(0, weight=1)

        self.dir_label = ttk.Label(dir_progress_frame, text="Download to: Not selected")
        self.dir_label.grid(row=0, column=0, sticky="ew")
        self.browse_button = ttk.Button(dir_progress_frame, text="Browse", command=self.browse_directory)
        self.browse_button.grid(row=0, column=1, padx=(0,5))

        self.progress_bar = ttk.Progressbar(dir_progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.grid(row=0, column=2, sticky="ew", padx=5)
        self.status_label = ttk.Label(dir_progress_frame, text="Ready")
        self.status_label.grid(row=0, column=3, sticky="e")

        # --- Playlist Frame (in dynamic_frame, initially hidden) ---
        self.playlist_frame = ttk.LabelFrame(dynamic_frame, text="Playlist Items")
        self.playlist_frame.grid(row=0, column=0, sticky='nsew', pady=5)
        playlist_buttons_frame = ttk.Frame(self.playlist_frame)
        playlist_buttons_frame.pack(fill="x", pady=5)
        ttk.Button(playlist_buttons_frame, text="Select All", command=self.select_all_playlist).pack(side="left", padx=5)
        ttk.Button(playlist_buttons_frame, text="Deselect All", command=self.deselect_all_playlist).pack(side="left")

        tree_frame = ttk.Frame(self.playlist_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.playlist_tree = HierarchicalChecklistTreeview(tree_frame, columns=("Title",), show="tree headings")
        self.playlist_tree.heading("Title", text="Video Title")
        self.playlist_tree.column("Title", anchor="w")
        self.playlist_tree.pack(side="left", fill="both", expand=True)
        self.playlist_tree.bind("<<TreeviewSelect>>", self.on_playlist_select)
        
        playlist_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.playlist_tree.yview)
        self.playlist_tree.configure(yscrollcommand=playlist_scrollbar.set)
        playlist_scrollbar.pack(side="right", fill="y")
        self.playlist_frame.grid_remove()

        # --- Log Viewer Frame (in dynamic_frame, initially hidden) ---
        self.log_frame = ttk.Frame(dynamic_frame)
        self.log_frame.grid(row=1, column=0, sticky='nsew', pady=5)
        log_text = ScrolledText(self.log_frame, height=8, state='disabled')
        log_text.pack(fill='both', expand=True)
        sys.stdout = StdoutRedirector(log_text)
        sys.stderr = StdoutRedirector(log_text)
        print("Log viewer initialized.")
        self.log_frame.grid_remove()

        self.downloader = Downloader(
            download_complete_callback=self.on_download_complete,
            progress_callback=self.update_progress_ui
        )

        try:
            self.media_player.set_hwnd(self.video_frame.winfo_id())
        except Exception as e:
            print(f"Error setting HWND for VLC: {e}")
            self.status_label.config(
                text="ERROR: VLC not found. Please install VLC Media Player."
            )
            self.play_pause_button.config(state="disabled")

        ffmpeg_ok, ffmpeg_message = self.validate_ffmpeg()
        if not ffmpeg_ok:
            self.status_label.config(text=f"ERROR: {ffmpeg_message}")
            self.download_button.config(state="disabled")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_log_viewer(self):
        if self.log_viewer_visible.get():
            self.log_frame.grid()
        else:
            self.log_frame.grid_remove()

    def change_theme(self, event=None):
        """Change the application theme."""
        try:
            theme = self.theme_style.get()
            if theme == "Vaporwave":
                self.apply_vaporwave_theme()
            elif theme == "Cyberpunk":
                self.apply_cyberpunk_theme()
            elif theme == "Hacker":
                self.apply_hacker_theme()
            elif theme == "Modern Dark":
                self.apply_modern_dark_theme()
            else:
                self.style.theme_use('clam')
        except Exception as e:
            print(f"Error changing theme: {e}")

    def apply_vaporwave_theme(self):
        """Apply a refined vaporwave theme with better readability."""
        BG = '#1c0b2b'
        FG = '#ff71ce'
        ACCENT1 = '#01cdfe'
        ACCENT2 = '#05ffa1'
        SELECT_BG = '#833ab4' # Darker purple for selection

        self.style.theme_use('clam')
        self.style.configure('.', background=BG, foreground=FG, fieldbackground='#2d1b3d', bordercolor=ACCENT1)
        self.style.configure('TFrame', background=BG)
        self.style.configure('TLabel', background=BG, foreground=FG)
        self.style.configure('TCheckbutton', background=BG, foreground=FG)
        self.style.configure('TLabelframe', background=BG, foreground=ACCENT1)
        self.style.configure('TLabelframe.Label', background=BG, foreground=ACCENT1)
        self.style.configure('TButton', background='#2d1b3d', foreground=ACCENT1, borderwidth=1)
        # Fix the blue text being hard to read by using a brighter cyan/white on hover
        self.style.map('TButton', background=[('active', ACCENT1)], foreground=[('active', '#ffffff')])
        self.style.configure('Treeview', background='#2d1b3d', foreground=FG, fieldbackground='#2d1b3d')
        self.style.map('Treeview', background=[('selected', SELECT_BG)], foreground=[('selected', '#ffffff')])
        # Combo contrast
        self.style.configure('TCombobox', fieldbackground='#2d1b3d', background='#2d1b3d', foreground=ACCENT1)
        self.style.map('TCombobox', fieldbackground=[('readonly', '#2d1b3d')], foreground=[('readonly', ACCENT1)])
        # Global popdown styling
        self.option_add('*TCombobox*Listbox.background', '#2d1b3d')
        self.option_add('*TCombobox*Listbox.foreground', ACCENT1)
        self.option_add('*TCombobox*Listbox.selectBackground', SELECT_BG)
        self.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
        
        # Treeview Headings
        self.style.configure('Treeview.Heading', background='#2d1b3d', foreground=ACCENT1, font=('Helvetica', 10, 'bold'))
        
        self.configure(background=BG)
        self.visualizer_canvas.configure(bg=BG)
        self.status_label.configure(foreground=ACCENT2)

    def apply_cyberpunk_theme(self):
        """Apply a neon cyberpunk theme."""
        BG = '#0a0a0a'
        FG = '#f0f0f0'
        YELLOW = '#f0db4f'
        PINK = '#ff0055'
        CYAN = '#00f6ff'

        self.style.theme_use('clam')
        self.style.configure('.', background=BG, foreground=FG, fieldbackground='#1a1a1a', bordercolor=PINK)
        self.style.configure('TFrame', background=BG)
        self.style.configure('TLabel', background=BG, foreground=CYAN)
        self.style.configure('TCheckbutton', background=BG, foreground=FG) # Set white foreground for readability
        self.style.map('TCheckbutton', foreground=[('active', PINK), ('normal', FG)])
        self.style.configure('TLabelframe', background=BG, foreground=YELLOW)
        self.style.configure('TLabelframe.Label', background=BG, foreground=YELLOW, font=('Helvetica', 12, 'bold'))
        self.style.configure('TButton', background='#1a1a1a', foreground=CYAN, borderwidth=1, bordercolor=CYAN)
        self.style.map('TButton', background=[('active', PINK)], foreground=[('active', BG)])
        self.style.configure('Treeview', background='#1a1a1a', foreground=FG, fieldbackground='#1a1a1a')
        self.style.map('Treeview', background=[('selected', PINK)], foreground=[('selected', BG)])
        self.style.configure('TCombobox', fieldbackground='#1a1a1a', background='#1a1a1a', foreground=CYAN)
        self.style.map('TCombobox', fieldbackground=[('readonly', '#1a1a1a')], foreground=[('readonly', CYAN)])
        # Global popdown styling
        self.option_add('*TCombobox*Listbox.background', '#1a1a1a')
        self.option_add('*TCombobox*Listbox.foreground', CYAN)
        self.option_add('*TCombobox*Listbox.selectBackground', PINK)
        self.option_add('*TCombobox*Listbox.selectForeground', BG)
        
        # Treeview Headings
        self.style.configure('Treeview.Heading', background='#1a1a1a', foreground=CYAN, font=('Helvetica', 10, 'bold'))
        
        self.configure(background=BG)
        self.visualizer_canvas.configure(bg=BG)
        self.status_label.configure(foreground=PINK)

    def apply_hacker_theme(self):
        """Apply a matrix code hacker theme with modern accents."""
        BG = '#000000'
        FG = '#00ff41'
        ACCENT = '#008f11'
        HIGHLIGHT = '#ffffff'

        self.style.theme_use('clam')
        self.style.configure('.', background=BG, foreground=FG, fieldbackground='#000a00', bordercolor=ACCENT)
        self.style.configure('TFrame', background=BG)
        self.style.configure('TLabel', background=BG, foreground=FG)
        self.style.configure('TCheckbutton', background=BG, foreground=FG)
        self.style.map('TCheckbutton', foreground=[('active', HIGHLIGHT), ('normal', FG)])
        self.style.configure('TLabelframe', background=BG, foreground=FG)
        self.style.configure('TLabelframe.Label', background=BG, foreground=FG, font=('Courier', 12, 'bold'))
        self.style.configure('TButton', background='#0a2a0a', foreground=FG, borderwidth=1)
        self.style.map('TButton', background=[('active', FG)], foreground=[('active', BG)])
        self.style.configure('Treeview', background='#000a00', foreground=FG, fieldbackground='#000a00', font=('Courier', 10))
        self.style.map('Treeview', background=[('selected', ACCENT)], foreground=[('selected', HIGHLIGHT)])
        self.style.configure('TCombobox', fieldbackground='#000a00', background='#000a00', foreground=FG)
        self.style.map('TCombobox', fieldbackground=[('readonly', '#000a00')], foreground=[('readonly', FG)])
        # Global popdown styling
        self.option_add('*TCombobox*Listbox.background', '#000a00')
        self.option_add('*TCombobox*Listbox.foreground', FG)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.option_add('*TCombobox*Listbox.selectForeground', HIGHLIGHT)

        # Treeview Headings
        self.style.configure('Treeview.Heading', background='#000a00', foreground=FG, font=('Courier', 10, 'bold'))
        self.configure(background=BG)
        self.visualizer_canvas.configure(bg=BG)
        self.status_label.configure(foreground="#32cd32")

    def apply_modern_dark_theme(self):
        """Apply a standard modern dark professional theme."""
        BG = '#1e1e1e'
        FG = '#ffffff'
        ACCENT = '#007acc'

        self.style.theme_use('clam')
        self.style.configure('.', background=BG, foreground=FG, fieldbackground='#2d2d2d', bordercolor=ACCENT)
        self.style.configure('TFrame', background=BG)
        self.style.configure('TLabel', background=BG, foreground=FG)
        self.style.configure('TLabelframe', background=BG, foreground=ACCENT)
        self.style.configure('TLabelframe.Label', background=BG, foreground=ACCENT)
        self.style.configure('TButton', background=ACCENT, foreground=FG)
        self.style.map('TButton', background=[('active', '#005a9e')])
        self.style.configure('Treeview', background='#2d2d2d', foreground=FG, fieldbackground='#2d2d2d')
        self.style.map('Treeview', background=[('selected', ACCENT)])
        self.style.configure('TCombobox', fieldbackground='#2d2d2d', background='#3d3d3d', foreground=FG)
        self.style.map('TCombobox', fieldbackground=[('readonly', '#2d2d2d')], foreground=[('readonly', FG)])
        # Global popdown styling
        self.option_add('*TCombobox*Listbox.background', '#2d2d2d')
        self.option_add('*TCombobox*Listbox.foreground', FG)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')

        # Treeview Headings
        self.style.configure('Treeview.Heading', background='#2d2d2d', foreground=ACCENT, font=('Helvetica', 10, 'bold'))
        
        self.configure(background=BG)
        self.visualizer_canvas.configure(bg=BG)

    def fetch_url_info(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Error: Please enter a URL first.")
            return
        
        # Reset UI state
        self.status_label.config(text="Fetching URL info...")
        self.fetch_button.config(state="disabled")
        self.playlist_frame.grid_remove()
        self.playlist_tree.delete(*self.playlist_tree.get_children())
        self.playlist_videos = []
        self.is_playlist = False

        thread = threading.Thread(target=self.fetch_url_info_thread, args=(url,))
        thread.start()

    def fetch_url_info_thread(self, url):
        """Fetch metadata for a URL using the yt-dlp Python API."""
        print(f"Fetching URL info thread started for: {url}")
        self.after(0, lambda: self.status_label.config(text="Fetching remote information..."))
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'ffmpeg_location': os.path.join(os.getcwd(), "ffmpeg.exe"),
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if not info:
                raise Exception("Could not extract information.")

            # Process based on type
            if info.get('_type') in ['playlist', 'multi_video'] or 'entries' in info:
                print(f"Processing as collection/channel (type: {info.get('_type', 'entries')})...")
                self.after(0, self.update_metadata, info)
                
                self.is_playlist = True
                new_entries = info.get('entries', [])
                
                # If this is a fresh fetch (not expanding), reset list
                # Use a flag if we are expanding? For now, if we are in this thread, we replace.
                self.playlist_videos = []
                for entry in new_entries:
                    if entry:
                        self.playlist_videos.append(entry)
                
                print(f"Found {len(self.playlist_videos)} entries.")
                self.after(0, self.populate_playlist_view)
                
                # If there's a first video and it's NOT a sub-playlist, prepare preview
                if self.playlist_videos:
                    first = self.playlist_videos[0]
                    if first.get('_type') != 'playlist' and first.get('ie_key') != 'YoutubeTab':
                        self.after(0, lambda: self.prepare_preview(first))
            else:
                # Single video
                print("Processing as single video...")
                self.after(0, self.update_metadata, info)
                self.is_playlist = False
                self.playlist_videos = [info]
                self.after(0, self.populate_playlist_view)
                self.after(0, lambda: self.prepare_preview(info))

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.after(0, lambda: self.status_label.config(text=error_msg))
            print(f"Fetch info error: {e}")
        finally:
            print("Fetching URL info thread finished.")
            self.after(0, lambda: self.fetch_button.config(state="normal"))

    def process_channel_info(self, info):
        self.playlist_frame.grid()
        self.playlist_tree.delete(*self.playlist_tree.get_children())
        self.playlist_videos = []

        playlists = {}
        videos = []

        if 'entries' in info:
            for entry in info['entries']:
                if entry.get('ie_key') == 'YoutubeTab':
                    continue
                if entry.get('_type') == 'playlist':
                    playlists[entry['id']] = {'title': entry['title'], 'videos': []}
                else:
                    videos.append(entry)

        # Create a top-level "All Videos" node
        all_videos_node = self.playlist_tree.insert("", "end", text=f"All Videos ({len(videos)})", open=False)
        for video in videos:
            video_index = len(self.playlist_videos)
            self.playlist_videos.append(video)
            self.playlist_tree.insert(all_videos_node, "end", text=video['title'], values=[video_index])

        # Create a top-level "Playlists" node
        playlists_node = self.playlist_tree.insert("", "end", text=f"Playlists ({len(playlists)})", open=False)
        for playlist_id, playlist_info in playlists.items():
            playlist_node = self.playlist_tree.insert(playlists_node, "end", text=f"{playlist_info['title']}", open=False)
            thread = threading.Thread(target=self.fetch_playlist_videos_thread, args=(playlist_id, playlist_node), daemon=True)
            thread.start()

        self.status_label.config(text=f"Channel info loaded.")

    def fetch_playlist_videos_thread(self, playlist_id, playlist_node):
        try:
            command = [
                'yt-dlp',
                '--quiet',
                '--dump-single-json',
                '--no-warnings',
                f'https://www.youtube.com/playlist?list={playlist_id}'
            ]

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

            for line in process.stdout:
                try:
                    video_info = json.loads(line)
                    self.after(0, self.add_video_to_playlist_tree, playlist_node, video_info)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Error fetching playlist videos: {e}")

    def add_video_to_playlist_tree(self, playlist_node, video_info):
        if not video_info or not isinstance(video_info, dict):
            return
        video_index = len(self.playlist_videos)
        self.playlist_videos.append(video_info)
        title = video_info.get('title', 'Untitled Video')
        self.playlist_tree.insert(playlist_node, "end", text=title, values=[video_index])



    def populate_playlist_view(self):
        self.playlist_frame.grid()
        self.playlist_tree.delete(*self.playlist_tree.get_children())
        for i, video in enumerate(self.playlist_videos):
            title = video.get('title', video.get('playlist_title', 'N/A'))
            # Distinguish between video and playlist/tab
            is_collection = video.get('_type') == 'playlist' or video.get('ie_key') == 'YoutubeTab'
            display_title = f"📁 {title}" if is_collection else title
            
            self.playlist_tree.insert("", "end", iid=i, text=display_title, values=[i])
        
        if self.is_playlist:
            # self.format_combo.config(state='disabled') # Keep enabled so user can set batch format
            self.status_label.config(text=f"Loaded {len(self.playlist_videos)} items. Click folders to expand.")
        else:
            self.format_combo.config(state='readonly')
            self.status_label.config(text="Single video info loaded.")
            # For a single video, check it by default
            if self.playlist_tree.get_children():
                self.playlist_tree.item(self.playlist_tree.get_children()[0], tags=("checked",))


    def on_playlist_select(self, event):
        selection = self.playlist_tree.selection()
        if not selection:
            return
        
        item_iid = selection[0]
        values = self.playlist_tree.item(item_iid, "values")
        if not values:
            return

        try:
            video_index = int(values[0])
            if video_index < len(self.playlist_videos):
                video_info = self.playlist_videos[video_index]
                
                # Check if it's a playlist/tab that needs expansion
                is_collection = video_info.get('_type') == 'playlist' or video_info.get('ie_key') == 'YoutubeTab'
                
                if is_collection:
                    url = video_info.get('url') or video_info.get('webpage_url')
                    if url:
                        self.status_label.config(text=f"Expanding {video_info.get('title')}...")
                        thread = threading.Thread(target=self.fetch_url_info_thread, args=(url,))
                        thread.start()
                else:
                    self.update_metadata(video_info)
                    # Preview selection
                    self.after(0, lambda: self.prepare_preview(video_info))
        except Exception as e:
            print(f"Playlist select error: {e}")

    def update_format_combo(self):
        """Helper method to update format combo for single videos"""
        if self.formats:
            format_texts = [f['text'] for f in self.formats]
            self.format_combo['values'] = format_texts
            if format_texts:
                self.format_combo.current(0)  # Select first format by default


    def select_all_playlist(self):
        for item in self.playlist_tree.get_children():
            self.playlist_tree.item(item, tags=("checked",))

    def deselect_all_playlist(self):
        for item in self.playlist_tree.get_children():
            self.playlist_tree.item(item, tags=("unchecked",))


    def extract_formats(self, info):
        formats = []
        seen_resolutions = set()
        
        # Add a "Best Quality" option
        formats.append({
            'format_id': 'bestvideo+bestaudio/best',
            'ext': 'mp4',
            'text': 'Best Available Quality (Auto)'
        })

        for f in info.get('formats', []):
            # Include formats with video
            if f.get('vcodec') != 'none':
                height = f.get('height')
                if height:
                    res_key = f"{height}p"
                    if res_key not in seen_resolutions:
                        format_text = f"{f.get('ext', 'mp4')} - {res_key}"
                        if f.get('fps'):
                            format_text += f" @ {f.get('fps')}fps"
                        
                        formats.append({
                            'format_id': f.get('format_id') if f.get('acodec') != 'none' else f"{f['format_id']}+bestaudio/best",
                            'ext': f.get('ext', 'mp4'),
                            'text': format_text
                        })
                        seen_resolutions.add(res_key)
        
        # Sort by resolution descending
        formats.sort(key=lambda x: int(x['text'].split('-')[1].split('p')[0]) if 'p' in x['text'] and '-' in x['text'] else 0, reverse=True)
        return formats

    def update_metadata(self, info):
        title = info.get('title', 'N/A')
        duration = info.get('duration', 0)
        thumbnail_url = info.get('thumbnail')
        self.formats = self.extract_formats(info)

        self.title_label.config(text=f"Title: {title}")
        duration_str = time.strftime('%H:%M:%S', time.gmtime(duration)) if duration else "N/A"
        self.duration_label.config(text=f"Duration: {duration_str}")

        if thumbnail_url:
            thread = threading.Thread(target=self.load_thumbnail, args=(thumbnail_url,))
            thread.start()
        
        self.update_format_combo()

    def load_thumbnail(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                image_data = response.read()
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((160, 90))
            self.thumbnail_photo = ImageTk.PhotoImage(img)
            self.after(0, lambda: self.thumbnail_label.config(image=self.thumbnail_photo))
        except Exception as e:
            self.after(0, lambda: self.thumbnail_label.config(text="Thumbnail\nfailed to load"))
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
            self.populate_library()

    def browse_computer(self):
        directory = filedialog.askdirectory()
        if directory:
            self.library_tree.delete(*self.library_tree.get_children())
            self.add_to_library_tree("", directory)

    def on_download_complete(self):
        """Called when all downloads in the current batch are finished."""
        self.after(0, lambda: self.status_label.config(text="All downloads complete."))
        self.after(0, self.populate_library)
        self.after(0, lambda: self.download_button.config(state="normal"))
        self.after(0, lambda: self.fetch_button.config(state="normal"))
        self.after(0, lambda: self.progress_bar.config(value=0))

    def update_progress_ui(self, d: dict):
        """
        Updates the progress bar and status label based on yt-dlp progress data.
        
        Args:
            d (dict): Progress data from yt-dlp.
        """
        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').replace('%','')
                progress_float = float(p)
                
                # Throttle UI updates to avoid lag
                current_time = time.time()
                if current_time - self.last_progress_update_time > 0.1 or progress_float >= 100:
                    self.after(0, lambda pf=progress_float: self.progress_bar.config(value=pf))
                    
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    status_text = f"Downloading: {p}% at {speed} (ETA: {eta})"
                    self.after(0, lambda st=status_text: self.status_label.config(text=st))
                    
                    self.last_progress_update_time = current_time
            except Exception as e:
                print(f"Progress update error: {e}")
        elif d['status'] == 'finished':
            self.after(0, lambda: self.status_label.config(text="Processing..."))
            self.after(0, lambda: self.progress_bar.config(value=100))

    def get_checked_videos(self):
        checked_videos = []
        all_items = []
        def get_all_items(parent_node=""):
            for item_iid in self.playlist_tree.get_children(parent_node):
                all_items.append(item_iid)
                get_all_items(item_iid)
        get_all_items()

        for item_iid in all_items:
            if "checked" in self.playlist_tree.item(item_iid, "tags"):
                if not self.playlist_tree.get_children(item_iid): # Is a leaf node
                    values = self.playlist_tree.item(item_iid, "values")
                    if values:
                        video_index = int(values[0])
                        if video_index < len(self.playlist_videos):
                            checked_videos.append(self.playlist_videos[video_index])
        return checked_videos

    def download_video(self):
        self._play_media_called = False
        if not self.download_dir:
            self.status_label.config(text="Error: Please select a download directory.")
            return

        self.download_button.config(state="disabled")
        self.fetch_button.config(state="disabled")

        videos_to_download = self.get_checked_videos()
        
        if not videos_to_download:
            self.status_label.config(text="Error: No items checked for download.")
            self.download_button.config(state="normal")
            self.fetch_button.config(state="normal")
            return
        
        self.status_label.config(text="Downloading in background...")
        
        # Get selected format ID
        format_id = None
        selected_format_text = self.format_combo.get()
        for f in self.formats:
            if f['text'] == selected_format_text:
                format_id = f['format_id']
                break
        
        self.downloader.download(
            videos_to_download, 
            self.download_dir, 
            self.mp3_var.get(), 
            self.is_playlist,
            format_id=format_id,
            write_subs=self.subtitle_var.get()
        )




    def prepare_preview(self, info):
        """Prepare the player to stream the video directly."""
        url = info.get('url') # This is the direct media URL from yt-dlp
        if url:
            self.downloaded_file_path = url
            self.play_media(is_stream=True)

    def play_media(self, is_stream=False):
        # Stop any currently running visualizer loop
        if self.visualizer_update_job:
            self.after_cancel(self.visualizer_update_job)
            self.visualizer_update_job = None

        if self.downloaded_file_path:
            self.is_visualizing = False # Reset visualizer flag
            
            # Apply volume immediately
            self.after(100, self.set_volume)
            
            # Use specific options for streaming vs local file
            if is_stream:
                media = self.vlc_instance.media_new(self.downloaded_file_path)
                self.status_label.config(text="Streaming preview...")
            else:
                if not os.path.exists(self.downloaded_file_path):
                    self.status_label.config(text="Error: Local file not found.")
                    return
                media = self.vlc_instance.media_new(self.downloaded_file_path)

            self.media_player.set_media(media)
            
            if not is_stream:
                # Only load audio data for visualization for local files (librosa doesn't love URLs)
                thread = threading.Thread(target=self.load_audio_data)
                thread.start()

            if self.mp3_var.get() and not is_stream:
                self.player_notebook.select(self.visualizer_frame)
                self.update_visualizer_ui() 
            else:
                self.player_notebook.select(self.video_frame)

            self.media_player.play()
            self.after(200, self.setup_seek_slider) 
            self.play_pause_button.config(text="❚❚ Pause")
            self.is_paused = False
        else:
            self.status_label.config(text="Error: No media path provided.")

    def on_tab_changed(self, event):
        selected_tab = self.player_notebook.tab(self.player_notebook.select(), "text")
        if selected_tab == "Audio Visualizer":
            self.update_visualizer_ui()
        else:
            if self.visualizer_update_job:
                self.after_cancel(self.visualizer_update_job)
                self.visualizer_update_job = None

    def load_audio_data(self):
        try:
            self.after(0, lambda: self.status_label.config(text="Loading audio for visualizer..."))
            self.audio_data, self.sample_rate = librosa.load(self.downloaded_file_path, sr=None)
            self.is_visualizing = True
            self.after(0, lambda: self.status_label.config(text="Playing audio."))
            tempo, self.beat_frames = librosa.beat.beat_track(y=self.audio_data, sr=self.sample_rate)
        except Exception as e:
            print(f"Error loading audio data: {e}")
            self.after(0, lambda: self.status_label.config(text="Error: Could not load audio for visualizer."))

    def visualize_audio(self):
        style = self.visualizer_style.get()
        if style == 'Bar':
            self.visualize_audio_bar()
        elif style == 'Heartbeat':
            self.visualize_audio_heartbeat()
        elif style == 'Spectrum':
            self.visualize_audio_spectrum()
        elif style == 'Oscilloscope':
            self.visualize_audio_oscilloscope()
        elif style == '3D':
            self.visualize_audio_3d()

    def visualize_audio_3d(self):
        if not self.is_visualizing or not self.media_player.is_playing() or self.audio_data is None:
            return

        current_time_ms = self.media_player.get_time()
        current_sample = int((current_time_ms / 1000.0) * self.sample_rate)
        chunk_size = 2048

        if current_sample + chunk_size > len(self.audio_data):
            return

        audio_chunk = self.audio_data[current_sample : current_sample + chunk_size]
        fft_result = np.fft.fft(audio_chunk)
        fft_result = np.abs(fft_result[:len(fft_result)//2])

        canvas = self.visualizer_canvas
        canvas.delete("all")
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        num_bars = 32
        bar_width = canvas_width / num_bars

        log_bands = [np.log1p(b) for b in fft_result]
        max_log_band = max(log_bands) if max(log_bands) > 0 else 1.0
        scaled_bands = [b / max_log_band for b in log_bands]

        for i in range(num_bars):
            band_index = i * (len(scaled_bands) // num_bars)
            height = scaled_bands[band_index] * canvas_height * 0.5

            # 3D effect
            x0 = i * bar_width
            y0 = canvas_height / 2 - height / 2
            x1 = x0 + bar_width
            y1 = y0 + height

            # Perspective
            perspective = i / num_bars
            x0 = x0 + perspective * 50
            x1 = x1 - perspective * 50

            # Color
            color_intensity = int(scaled_bands[band_index] * 255)
            color = f'#{color_intensity:02x}{0:02x}{255-color_intensity:02x}'

            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

    def visualize_audio_bar(self):
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
        
        # We only need the positive frequencies
        fft_result = np.abs(fft_result[:len(fft_result)//2])

        # Group frequencies into bands for visualization
        num_bands = 128 # Increased bands for skinnier look
        band_width = len(fft_result) // num_bands
        bands = [np.mean(fft_result[i*band_width:(i+1)*band_width]) for i in range(num_bands)]
        
        # --- Drawing on Canvas ---
        canvas = self.visualizer_canvas
        canvas.delete("all")
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        # Logarithmic scaling for sensitivity
        log_bands = [np.log1p(b) for b in bands]
        max_log_band = max(log_bands) if max(log_bands) > 0 else 1.0
        scaled_bands = [b / max_log_band for b in log_bands]

        # Bar width and gap
        total_bar_width = canvas_width / num_bands
        bar_width = total_bar_width * 0.5 # Bars take up 50% of their space
        gap_width = total_bar_width * 0.5

        for i, height in enumerate(scaled_bands):
            x0 = i * total_bar_width + (gap_width / 2)
            y0 = canvas_height
            x1 = x0 + bar_width
            y1 = canvas_height - (height * canvas_height * 0.9)
            
            # Gradient color
            color_intensity = int(height * 255)
            color = f'#{0:02x}{color_intensity:02x}{255-color_intensity:02x}' # Blue to Green gradient
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

    def visualize_audio_heartbeat(self):
        if not self.is_visualizing or not self.media_player.is_playing() or self.audio_data is None or self.beat_frames is None:
            return

        current_time_ms = self.media_player.get_time()
        current_sample = int((current_time_ms / 1000.0) * self.sample_rate)

        canvas = self.visualizer_canvas
        canvas.delete("all")
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        # Convert beat frames to samples
        beat_samples = librosa.frames_to_samples(self.beat_frames)

        # Find the closest beat
        closest_beat_sample = -1
        if len(beat_samples) > 0:
            closest_beat_sample = beat_samples[np.argmin(np.abs(beat_samples - current_sample))]

        # Draw a sweeping line
        line_pos = (current_time_ms % 2000) / 2000 * canvas_width
        canvas.create_line(line_pos, 0, line_pos, canvas_height, fill="#00ff00", width=2)

        # Draw a blip on the beat
        if closest_beat_sample != -1:
            samples_since_beat = np.abs(current_sample - closest_beat_sample)
            if samples_since_beat < self.sample_rate * 0.1: # Blip for 100ms
                blip_height = (1 - (samples_since_beat / (self.sample_rate * 0.1))) * (canvas_height / 4)
                canvas.create_line(line_pos, canvas_height / 2 - blip_height, line_pos, canvas_height / 2 + blip_height, fill="#ff0000", width=4)

    def visualize_audio_spectrum(self):
        if not self.is_visualizing or not self.media_player.is_playing() or self.audio_data is None:
            return

        current_time_ms = self.media_player.get_time()
        current_sample = int((current_time_ms / 1000.0) * self.sample_rate)
        chunk_size = 2048

        if current_sample + chunk_size > len(self.audio_data):
            return

        audio_chunk = self.audio_data[current_sample : current_sample + chunk_size]
        fft_result = np.fft.fft(audio_chunk)
        fft_result = np.abs(fft_result[:len(fft_result)//2])

        canvas = self.visualizer_canvas
        canvas.delete("all")
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        # Logarithmic scaling for sensitivity
        log_bands = [np.log1p(b) for b in fft_result]
        max_log_band = max(log_bands) if max(log_bands) > 0 else 1.0
        scaled_bands = [b / max_log_band for b in log_bands]

        points = []
        for i, height in enumerate(scaled_bands):
            x = (i / len(scaled_bands)) * canvas_width
            y = canvas_height - (height * canvas_height * 0.9)
            points.extend([x, y])

        if len(points) > 2:
            canvas.create_line(points, fill="#00ff00")

    def visualize_audio_oscilloscope(self):
        if not self.is_visualizing or not self.media_player.is_playing() or self.audio_data is None:
            return

        current_time_ms = self.media_player.get_time()
        current_sample = int((current_time_ms / 1000.0) * self.sample_rate)
        chunk_size = 1024

        if current_sample + chunk_size > len(self.audio_data):
            return

        audio_chunk = self.audio_data[current_sample : current_sample + chunk_size]

        canvas = self.visualizer_canvas
        canvas.delete("all")
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        # Normalize the audio chunk
        max_amplitude = np.max(np.abs(audio_chunk))
        if max_amplitude == 0:
            return # Avoid division by zero
        normalized_chunk = audio_chunk / max_amplitude

        # Draw the waveform
        points = []
        for i, sample in enumerate(normalized_chunk):
            x = (i / (chunk_size - 1)) * canvas_width
            y = (sample + 1) / 2 * canvas_height
            points.extend([x, y])

        canvas.create_line(points, fill="#00ff00")

    def play_pause(self, force_play=False):
        # If no media is in the player, load the last downloaded file.
        if not self.media_player.get_media():
            if self.downloaded_file_path and os.path.exists(self.downloaded_file_path):
                self.play_media() # play_media will load and play
                return
            else:
                self.status_label.config(text="Error: No media file loaded or found.")
                return

        if self.media_player.is_playing() and not force_play:
            self.media_player.pause()
            self.play_pause_button.config(text="▶ Play")
            self.is_paused = True
        else:
            if self.media_player.play() == -1:
                # If playing fails, it might be because the media hasn't been set yet.
                if self.downloaded_file_path and os.path.exists(self.downloaded_file_path):
                    self.play_media()
                else:
                    self.status_label.config(text="Error: Cannot play media.")
                return
            self.play_pause_button.config(text="❚❚ Pause")
            self.is_paused = False

    def toggle_shuffle(self):
        self.is_shuffling = not self.is_shuffling
        self.shuffle_button.config(relief="sunken" if self.is_shuffling else "raised")

    def toggle_repeat(self):
        self.is_repeating = not self.is_repeating
        self.repeat_button.config(relief="sunken" if self.is_repeating else "raised")

    def media_ended(self, event):
        if self.is_repeating:
            self.play_media()
        else:
            self.play_next()

    def play_next(self):
        if self.is_playing_from_library:
            if self.is_shuffling:
                all_items = self.get_all_library_items()
                if all_items:
                    next_item = random.choice(all_items)
                    self.library_tree.selection_set(next_item)
                    self.library_tree.focus(next_item)
            else:
                current_item = self.library_tree.focus()
                next_item = self.library_tree.next(current_item)
                if next_item:
                    self.library_tree.selection_set(next_item)
                    self.library_tree.focus(next_item)
        else:
            if self.is_shuffling:
                if self.playlist_videos:
                    next_video = random.choice(self.playlist_videos)
                    self.downloaded_file_path = os.path.join(self.download_dir, f"{next_video.get('title')}.mp4")
                    self.mp3_var.set(False)
                    self.play_media()
            else:
                current_index = -1
                for i, video in enumerate(self.playlist_videos):
                    if self.downloaded_file_path and video.get('title') in self.downloaded_file_path:
                        current_index = i
                        break
                
                if current_index != -1 and current_index + 1 < len(self.playlist_videos):
                    next_video = self.playlist_videos[current_index + 1]
                    self.downloaded_file_path = os.path.join(self.download_dir, f"{next_video.get('title')}.mp4")
                    self.mp3_var.set(False)
                    self.play_media()

    def play_previous(self):
        if self.is_playing_from_library:
            current_item = self.library_tree.focus()
            prev_item = self.library_tree.prev(current_item)
            if prev_item:
                self.library_tree.selection_set(prev_item)
                self.library_tree.focus(prev_item)
        else:
            current_index = -1
            for i, video in enumerate(self.playlist_videos):
                if self.downloaded_file_path and video.get('title') in self.downloaded_file_path:
                    current_index = i
                    break
            
            if current_index > 0:
                prev_video = self.playlist_videos[current_index - 1]
                self.downloaded_file_path = os.path.join(self.download_dir, f"{prev_video.get('title')}.mp4")
                self.mp3_var.set(False)
                self.play_media()

    def get_all_library_items(self, parent=""):
        items = []
        for item in self.library_tree.get_children(parent):
            items.append(item)
            items.extend(self.get_all_library_items(item))
        return items

    def populate_library(self):
        for i in self.library_tree.get_children():
            self.library_tree.delete(i)

        if self.download_dir:
            self.add_to_library_tree("", self.download_dir)

    def add_to_library_tree(self, parent, path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                node = self.library_tree.insert(parent, "end", text=item, open=False)
                self.add_to_library_tree(node, item_path)
            else:
                self.library_tree.insert(parent, "end", text=item, values=[item_path])

    def on_library_select(self, event):
        selection = self.library_tree.selection()
        if not selection:
            return
        
        item = self.library_tree.item(selection[0])
        file_path = item.get("values")[0] if item.get("values") else None

        if file_path and os.path.isfile(file_path):
            self.media_player.stop() # Stop the currently playing media
            self.downloaded_file_path = file_path
            self.mp3_var.set(file_path.endswith('.mp3'))
            self.is_playing_from_library = True
            self.play_media()

    def setup_seek_slider(self):
        """Initialize the seek slider with proper range when media is loaded"""
        length = self.media_player.get_length()
        if length > 0:
            self.seek_slider.config(to=length)
            self.seek_slider.set(0)
            self.update_seek_slider()
        else:
            self.after(100, self.setup_seek_slider)

    def update_seek_slider(self):
        """Update the seek slider position during playback using polling."""
        # Only update if media is loaded and we're not manually seeking
        if self.media_player.get_media() and not self.is_seeking:
            length = self.media_player.get_length()
            if length > 0:
                # Update slider range if it changed
                current_max = self.seek_slider.cget('to')
                if current_max != length:
                    self.seek_slider.config(to=length)
                
                # Get current position and update slider
                position = self.media_player.get_time()
                self.seek_var.set(position)  # This won't trigger command now!
                
                # Update time label
                current_time_str = time.strftime('%M:%S', time.gmtime(position / 1000))
                total_time_str = time.strftime('%M:%S', time.gmtime(length / 1000))
                self.time_label.config(text=f"{current_time_str} / {total_time_str}")
        
        # Schedule next update (polling pattern)
        if self.media_player.is_playing() or self.is_paused:
            self.after(100, self.update_seek_slider)  # Poll every 100ms

    def on_seek_start(self, event):
        """User started dragging seek bar."""
        self.is_seeking = True
        
    def on_seek_motion(self, event):
        """Called while user is dragging the seek slider"""
        if self.is_seeking and self.media_player.get_media():
            length = self.media_player.get_length()
            if length > 0:
                try:
                    pos = self.seek_var.get()
                    pos = max(0, min(pos, length))
                    current_time_str = time.strftime('%M:%S', time.gmtime(pos / 1000))
                    total_time_str = time.strftime('%M:%S', time.gmtime(length / 1000))
                    self.time_label.config(text=f"{current_time_str} / {total_time_str}")
                except:
                    pass
        return "break"

    def on_seek_end(self, event):
        """User released seek bar."""
        if self.is_seeking and self.media_player.get_media():
            try:
                new_position = int(self.seek_var.get())
                length = self.media_player.get_length()
                if length > 0:
                    new_position = max(0, min(new_position, length))
                if self.media_player.is_seekable():
                    self.media_player.set_time(new_position)
            except Exception as e:
                print(f"Seek error: {e}")
        self.is_seeking = False
        return "break"


    def set_volume(self):
        """Set the media player volume"""
        try:
            volume_int = int(self.volume_var.get())
            self.media_player.audio_set_volume(volume_int)
        except Exception as e:
            print(f"Volume error: {e}")

    def debug_controls(self):
        """Helper method to debug control values and player state."""
        print(f"Seek slider value: {self.seek_slider.get()}")
        print(f"Seek slider max: {self.seek_slider.cget('to')}")
        print(f"Volume slider value: {self.volume_slider.get()}")
        if self.media_player.get_media():
            print(f"Media position: {self.media_player.get_time()} ms")
            print(f"Media length: {self.media_player.get_length()} ms")
            print(f"Media volume: {self.media_player.audio_get_volume()}")
        else:
            print("No media loaded.")

    def update_visualizer_ui(self):
        """Fast update loop for the audio visualizer animation."""
        if self.is_visualizing:
            self.visualize_audio()
        self.visualizer_update_job = self.after(40, self.update_visualizer_ui)


    def validate_ffmpeg(self):
        """Validate ffmpeg is executable and working."""
        ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
        
        if not os.path.exists(ffmpeg_path):
            return False, "ffmpeg.exe not found in project directory"
        
        try:
            # Test execution
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, "ffmpeg exists but is not executable"
            return True, "ffmpeg OK"
        except Exception as e:
            return False, f"ffmpeg validation failed: {str(e)}"

    def on_closing(self):
        """
        Clean up resources before application exits.
        
        Ensures:
        - VLC player is stopped and released
        - All scheduled callbacks are cancelled
        - Threads are notified to stop
        - Window closes gracefully
        """
        print("Cleaning up resources...")
        
        # Stop visualizer updates
        if self.visualizer_update_job:
            self.after_cancel(self.visualizer_update_job)
            self.visualizer_update_job = None
        
        # Stop and release VLC player
        if self.media_player:
            try:
                self.media_player.stop()
                self.media_player.release()
            except Exception as e:
                print(f"Error stopping VLC: {e}")
        
        # Release VLC instance
        if self.vlc_instance:
            try:
                self.vlc_instance.release()
            except Exception as e:
                print(f"Error releasing VLC instance: {e}")
        
        # Stop visualizer flag
        self.is_visualizing = False
        
        # Note: Daemon threads will exit automatically, but we set is_visualizing
        # to False to ensure they stop gracefully if they check this flag
        
        print("Cleanup complete. Exiting.")
        
        # Destroy window
        self.destroy()


if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()
