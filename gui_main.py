import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap
from stack_queue import RecentlyPlayed
from player import MusicPlayer
import threading
import time

SONG_DIR = "songs"

class SpotifyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Music Manager - Spotify Style")
        self.root.geometry("900x500")
        self.root.configure(bg="#121212")

        # Core modules
        self.playlist = Playlist()
        self.song_map = SongMap()
        self.history = RecentlyPlayed()
        self.heap = SongHeap()
        self.player = MusicPlayer()
        self.current_node = None
        self.playing = False

        # UI
        self.create_ui()
        self.load_songs()

    def create_ui(self):
        # Left sidebar
        self.sidebar = tk.Frame(self.root, bg="#1e1e1e", width=220)
        self.sidebar.pack(side="left", fill="y")

        tk.Label(self.sidebar, text="🎵 Playlist", font=("Segoe UI", 16, "bold"),
                 bg="#1e1e1e", fg="#FFD700").pack(pady=10)

        self.listbox = tk.Listbox(self.sidebar, bg="#2c2c2c", fg="white",
                                  selectbackground="#FF4500", font=("Consolas", 12))
        self.listbox.pack(fill="both", expand=True, padx=10, pady=5)

        # Main area
        self.main_area = tk.Frame(self.root, bg="#121212")
        self.main_area.pack(side="right", fill="both", expand=True)

        # Album cover
        self.cover_label = tk.Label(self.main_area, bg="#121212")
        self.cover_label.pack(pady=20)

        # Current song label
        self.current_label = tk.Label(self.main_area, text="No song playing",
                                      font=("Segoe UI", 16, "bold"), fg="white", bg="#121212")
        self.current_label.pack(pady=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("orange.Horizontal.TProgressbar", troughcolor="#2c2c2c", background="#FF4500", thickness=10)
        self.progress_bar = ttk.Progressbar(self.main_area, variable=self.progress_var, maximum=100,
                                            style="orange.Horizontal.TProgressbar", length=600)
        self.progress_bar.pack(pady=10)

        # Bottom control bar
        control_frame = tk.Frame(self.main_area, bg="#121212")
        control_frame.pack(pady=10)

        btn_style = {"width": 6, "font": ("Segoe UI", 12, "bold"), "bg": "#FF4500", "fg": "white"}
        tk.Button(control_frame, text="⏴", command=self.prev_song, **btn_style).grid(row=0, column=0, padx=5)
        tk.Button(control_frame, text="▶", command=self.play_selected, **btn_style).grid(row=0, column=1, padx=5)
        tk.Button(control_frame, text="⏸", command=self.pause_song, **btn_style).grid(row=0, column=2, padx=5)
        tk.Button(control_frame, text="⏵", command=self.next_song, **btn_style).grid(row=0, column=3, padx=5)

        # Volume
        volume_frame = tk.Frame(self.main_area, bg="#121212")
        volume_frame.pack(pady=10)
        tk.Label(volume_frame, text="Volume", fg="white", bg="#121212").pack(side="left")
        self.volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient="horizontal",
                                      bg="#121212", fg="white", troughcolor="#555555", command=self.set_volume)
        self.volume_slider.set(80)
        self.volume_slider.pack(side="left")

    def load_songs(self):
        if not os.path.exists(SONG_DIR):
            os.makedirs(SONG_DIR)
        self.playlist.load_from_folder(SONG_DIR)
        self.song_map.rebuild_from_playlist(self.playlist)
        self.listbox.delete(0, tk.END)
        cur = self.playlist.head
        toggle_color = True
        while cur:
            self.listbox.insert(tk.END, cur.title)
            if toggle_color:
                self.listbox.itemconfig(tk.END, bg="#2c2c2c")
            toggle_color = not toggle_color
            cur = cur.next
        if self.listbox.size() == 0:
            self.listbox.insert(tk.END, "No songs found in songs/ folder")

    def play_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            messagebox.showinfo("Info", "Select a song first.")
            return
        title = self.listbox.get(idx)
        node = self.song_map.search_song(title)
        if not node:
            messagebox.showerror("Error", "Song not found.")
            return
        self.play_node(node)

    def play_node(self, node):
        self.current_node = node
        self.current_label.config(text=f"🎶 {node.title}")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        self.playing = True
        threading.Thread(target=self.update_progress, daemon=True).start()

    def update_progress(self):
        self.progress_var.set(0)
        while self.playing and self.player.is_playing():
            self.progress_var.set(min(100, self.progress_var.get() + 1))
            time.sleep(0.5)
        self.progress_var.set(0)

    def pause_song(self):
        self.player.pause()
        self.playing = False

    def stop_song(self):
        self.player.stop()
        self.playing = False
        self.progress_var.set(0)

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.play_node(self.current_node.next)
        else:
            messagebox.showinfo("Info", "This is the last song.")

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.play_node(self.current_node.prev)
        else:
            messagebox.showinfo("Info", "This is the first song.")

    def set_volume(self, val):
        self.player.set_volume(int(val)/100)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyGUI(root)
    root.mainloop()
