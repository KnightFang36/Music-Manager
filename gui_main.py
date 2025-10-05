import os
import tkinter as tk
from tkinter import ttk, messagebox
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap, SongBST
from stack_queue import RecentlyPlayed, UpcomingSongs
from player import MusicPlayer
from main import init_music_manager, save_play_counts
import threading
import time

SONG_DIR = 'songs'

class MusicManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Manager")
        self.root.geometry("800x500")
        self.root.configure(bg="#121212")

        # Backend
        (self.playlist, self.song_map, self.history,
         self.upcoming, self.heap, self.bst, self.player) = init_music_manager()
        self.current_node = None

        # Playback
        self.playback_thread = None
        self.playing = False

        self.create_widgets()
        self.load_songs()
        self.update_progress_bar()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Header
        tk.Label(self.root, text="🎵 Music Manager", font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#121212").pack(pady=10)

        # Main Frame
        main_frame = tk.Frame(self.root, bg="#121212")
        main_frame.pack(fill="both", expand=True, padx=10)

        # Playlist Listbox
        playlist_frame = tk.Frame(main_frame, bg="#121212")
        playlist_frame.pack(side="left", fill="both", expand=True)
        tk.Label(playlist_frame, text="Playlist", fg="white", bg="#121212").pack()
        self.playlist_box = tk.Listbox(playlist_frame, bg="#1e1e1e", fg="white", font=("Consolas", 11),
                                       selectbackground="#0078D7", activestyle="none")
        self.playlist_box.pack(fill="both", expand=True, pady=5)

        # Upcoming Listbox
        upcoming_frame = tk.Frame(main_frame, bg="#121212")
        upcoming_frame.pack(side="left", fill="y", padx=10)
        tk.Label(upcoming_frame, text="Upcoming Queue", fg="white", bg="#121212").pack()
        self.upcoming_box = tk.Listbox(upcoming_frame, bg="#1e1e1e", fg="white", font=("Consolas", 11),
                                       selectbackground="#0078D7", height=15)
        self.upcoming_box.pack(fill="y", pady=5)

        # BST view
        bst_frame = tk.Frame(main_frame, bg="#121212")
        bst_frame.pack(side="left", fill="y")
        tk.Label(bst_frame, text="Alphabetical", fg="white", bg="#121212").pack()
        self.bst_box = tk.Listbox(bst_frame, bg="#1e1e1e", fg="white", font=("Consolas", 11),
                                  selectbackground="#0078D7", height=15)
        self.bst_box.pack(fill="y", pady=5)

        # Controls
        ctrl_frame = tk.Frame(self.root, bg="#121212")
        ctrl_frame.pack(pady=10)

        style = {"width": 10, "font": ("Segoe UI", 10, "bold"), "bg": "#0078D7", "fg": "white"}

        tk.Button(ctrl_frame, text="▶ Play", command=self.play_selected, **style).grid(row=0, column=0, padx=5)
        tk.Button(ctrl_frame, text="⏸ Pause", command=self.pause_song, **style).grid(row=0, column=1, padx=5)
        tk.Button(ctrl_frame, text="⏹ Stop", command=self.stop_song, **style).grid(row=0, column=2, padx=5)
        tk.Button(ctrl_frame, text="⏵ Next", command=self.next_song, **style).grid(row=0, column=3, padx=5)
        tk.Button(ctrl_frame, text="⏴ Prev", command=self.prev_song, **style).grid(row=0, column=4, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, maximum=100, variable=self.progress_var)
        self.progress_bar.pack(fill="x", padx=10, pady=5)

        # Volume
        volume_frame = tk.Frame(self.root, bg="#121212")
        volume_frame.pack(pady=5)
        tk.Label(volume_frame, text="Volume", fg="white", bg="#121212").pack(side="left")
        self.volume_slider = tk.Scale(volume_frame, from_=0, to=1, resolution=0.01, orient="horizontal",
                                      command=self.set_volume, bg="#121212", fg="white")
        self.volume_slider.set(0.5)
        self.volume_slider.pack(side="left")

        # Status
        self.status_label = tk.Label(self.root, text="No song playing", bg="#121212", fg="lightgray",
                                     font=("Segoe UI", 10))
        self.status_label.pack(pady=5)

    def load_songs(self):
        # Playlist
        self.playlist_box.delete(0, tk.END)
        cur = self.playlist.head
        while cur:
            self.playlist_box.insert(tk.END, cur.title)
            cur = cur.next
        if self.playlist_box.size() == 0:
            self.playlist_box.insert(tk.END, "No songs found")

        # BST
        self.update_bst_box()
        # Upcoming
        self.update_upcoming_box()

    def update_bst_box(self):
        self.bst_box.delete(0, tk.END)
        for title in sorted(self.song_map.hashmap.keys()):
            self.bst_box.insert(tk.END, title)

    def update_upcoming_box(self):
        self.upcoming_box.delete(0, tk.END)
        for i, title in enumerate(self.upcoming.queue):
            self.upcoming_box.insert(tk.END, f"{i+1}. {title}")

    def play_selected(self):
        idx = self.playlist_box.curselection()
        if not idx:
            messagebox.showinfo("Info", "Select a song first.")
            return
        title = self.playlist_box.get(idx)
        node = self.song_map.search_song(title)
        if not node:
            messagebox.showerror("Error", "Song not found.")
            return
        self.current_node = node
        self.start_playback(node)

    def start_playback(self, node):
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        self.status_label.config(text=f"Playing: {node.title}")
        self.playing = True

    def pause_song(self):
        self.player.pause()
        self.status_label.config(text="Paused")

    def stop_song(self):
        self.player.stop()
        self.status_label.config(text="Stopped")
        self.playing = False

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.current_node = self.current_node.next
            self.start_playback(self.current_node)
        else:
            messagebox.showinfo("Info", "This is the last song.")

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.current_node = self.current_node.prev
            self.start_playback(self.current_node)
        else:
            messagebox.showinfo("Info", "This is the first song.")

    def set_volume(self, val):
        self.player.set_volume(float(val))

    def update_progress_bar(self):
        if self.playing and self.player.is_playing():
            self.progress_var.set(self.player.get_progress()*100)
        else:
            self.progress_var.set(0)
        self.root.after(500, self.update_progress_bar)

    def on_close(self):
        self.stop_song()
        save_play_counts(self.heap)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicManagerGUI(root)
    root.mainloop()
