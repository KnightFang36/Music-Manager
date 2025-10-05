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
COVER_DIR = "covers"

class MusicManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Music Manager Pro")
        self.root.geometry("800x400")
        self.root.configure(bg="#121212")

        # Core modules
        self.playlist = Playlist()
        self.song_map = SongMap()
        self.history = RecentlyPlayed()
        self.heap = SongHeap()
        self.player = MusicPlayer()
        self.current_node = None
        self.current_cover = None
        self.playing = False

        # UI
        self.create_widgets()
        self.load_songs()

    def create_widgets(self):
        # Split layout
        self.left_frame = tk.Frame(self.root, bg="#1e1e1e", width=300)
        self.left_frame.pack(side="left", fill="y")

        self.right_frame = tk.Frame(self.root, bg="#121212")
        self.right_frame.pack(side="right", fill="both", expand=True)

        # Playlist label
        tk.Label(self.left_frame, text="🎵 Playlist", font=("Segoe UI", 16, "bold"),
                 fg="#FFD700", bg="#1e1e1e").pack(pady=10)

        # Playlist listbox
        self.scrollbar = tk.Scrollbar(self.left_frame)
        self.scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(self.left_frame, bg="#2c2c2c", fg="white", font=("Consolas", 11),
                                  selectbackground="#FF4500", activestyle="none", width=35)
        self.listbox.pack(side="left", fill="y", expand=True)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)

        # Right frame: Cover, progress, controls
        self.cover_label = tk.Label(self.right_frame, bg="#121212")
        self.cover_label.pack(pady=10)

        # Current song label
        self.status_label = tk.Label(self.right_frame, text="No song playing", font=("Segoe UI", 14, "bold"),
                                     fg="white", bg="#121212")
        self.status_label.pack(pady=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.right_frame, variable=self.progress_var, maximum=100,
                                            length=400, style="orange.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=10)

        # Buttons frame
        btn_frame = tk.Frame(self.right_frame, bg="#121212")
        btn_frame.pack(pady=10)

        style = {"width": 10, "font": ("Segoe UI", 10, "bold"), "bg": "#FF4500", "fg": "white"}
        tk.Button(btn_frame, text="▶ Play", command=self.play_selected, **style).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="⏸ Pause", command=self.pause_song, **style).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="⏹ Stop", command=self.stop_song, **style).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="⏵ Next", command=self.next_song, **style).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="⏴ Prev", command=self.prev_song, **style).grid(row=0, column=4, padx=5)

        # Volume slider
        vol_frame = tk.Frame(self.right_frame, bg="#121212")
        vol_frame.pack(pady=5)
        tk.Label(vol_frame, text="Volume", fg="white", bg="#121212").pack(side="left", padx=5)
        self.volume_slider = tk.Scale(vol_frame, from_=0, to=100, orient="horizontal", bg="#121212",
                                      fg="white", troughcolor="#555555", command=self.set_volume)
        self.volume_slider.set(80)
        self.volume_slider.pack(side="left")

        # Progress bar style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("orange.Horizontal.TProgressbar", troughcolor="#1e1e1e", background="#FF4500")

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

    def show_cover(self, song_title):
        img_path = os.path.join(COVER_DIR, f"{song_title}.jpg")
        if not os.path.exists(img_path):
            self.cover_label.config(image="", text="🎵 No Cover", font=("Segoe UI", 16), fg="white")
            return
        img = Image.open(img_path)
        img = img.resize((200, 200))
        self.current_cover = ImageTk.PhotoImage(img)
        self.cover_label.config(image=self.current_cover, text="")

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
        self.status_label.config(text=f"🎶 Now Playing: {node.title}")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        self.show_cover(node.title)
        self.playing = True
        threading.Thread(target=self.update_progress, daemon=True).start()

    def update_progress(self):
        # Simulated progress bar (pygame cannot give exact duration easily)
        self.progress_var.set(0)
        while self.playing and self.player.is_playing():
            self.progress_var.set(min(100, self.progress_var.get() + 1))
            time.sleep(0.5)
        self.progress_var.set(0)

    def pause_song(self):
        self.player.pause()
        self.status_label.config(text="⏸ Paused")
        self.playing = False

    def stop_song(self):
        self.player.stop()
        self.status_label.config(text="⏹ Stopped")
        self.playing = False
        self.progress_var.set(0)

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.play_node(self.current_node.next)
        else:
            messagebox.showinfo("Info", "This is the last song in playlist.")

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.play_node(self.current_node.prev)
        else:
            messagebox.showinfo("Info", "This is the first song in playlist.")

    def set_volume(self, val):
        vol = int(val) / 100
        self.player.set_volume(vol)

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicManagerGUI(root)
    root.mainloop()
