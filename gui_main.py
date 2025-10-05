# gui_main.py
import os
import tkinter as tk
from tkinter import ttk, messagebox
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap
from stack_queue import RecentlyPlayed
from player import MusicPlayer
from main import init_music_manager, save_play_counts

SONG_DIR = 'songs'

class MusicManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Manager")
        self.root.geometry("600x450")
        self.root.configure(bg="#121212")

        # Core backend
        (self.playlist, self.song_map, self.history,
         self.upcoming, self.heap, self.bst, self.player) = init_music_manager()
        self.current_node = None

        self.create_widgets()
        self.load_songs()

        # Save on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        tk.Label(self.root, text="🎵 Music Manager", font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#121212").pack(pady=10)

        frame = tk.Frame(self.root, bg="#121212")
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(frame, bg="#1e1e1e", fg="white", font=("Consolas", 11),
                                  selectbackground="#0078D7", activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        btn_frame = tk.Frame(self.root, bg="#121212")
        btn_frame.pack(pady=15)

        style = {"width": 10, "font": ("Segoe UI", 10, "bold"), "bg": "#0078D7", "fg": "white"}

        tk.Button(btn_frame, text="▶ Play", command=self.play_selected, **style).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="⏸ Pause", command=self.pause_song, **style).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="⏹ Stop", command=self.stop_song, **style).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="⏵ Next", command=self.next_song, **style).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="⏴ Prev", command=self.prev_song, **style).grid(row=0, column=4, padx=5)

        self.status_label = tk.Label(self.root, text="No song playing", bg="#121212", fg="lightgray",
                                     font=("Segoe UI", 10))
        self.status_label.pack(pady=10)

    def load_songs(self):
        self.listbox.delete(0, tk.END)
        cur = self.playlist.head
        while cur:
            self.listbox.insert(tk.END, cur.title)
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
        self.current_node = node
        self.status_label.config(text=f"Playing: {node.title}")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)

    def pause_song(self):
        self.player.pause()
        self.status_label.config(text="Paused")

    def stop_song(self):
        self.player.stop()
        self.status_label.config(text="Stopped")

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.current_node = self.current_node.next
            self.status_label.config(text=f"Playing: {self.current_node.title}")
            self.player.play(self.current_node.path)
            self.history.push(self.current_node.title)
            self.heap.add_play(self.current_node.title)
        else:
            messagebox.showinfo("Info", "This is the last song in playlist.")

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.current_node = self.current_node.prev
            self.status_label.config(text=f"Playing: {self.current_node.title}")
            self.player.play(self.current_node.path)
            self.history.push(self.current_node.title)
            self.heap.add_play(self.current_node.title)
        else:
            messagebox.showinfo("Info", "This is the first song in playlist.")

    def on_close(self):
        self.player.stop()
        save_play_counts(self.heap)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicManagerGUI(root)
    root.mainloop()
