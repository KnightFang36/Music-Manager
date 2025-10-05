# gui_main.py
# Basic Tkinter GUI for Music Manager

import os
import tkinter as tk
from tkinter import ttk, messagebox
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap, SongBST
from stack_queue import RecentlyPlayed
from player import MusicPlayer

SONG_DIR = 'songs'


class MusicManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Manager")
        self.root.geometry("700x500")
        self.root.configure(bg="#121212")

        # Core modules
        self.playlist = Playlist()
        self.song_map = SongMap()
        self.history = RecentlyPlayed()
        self.heap = SongHeap()
        self.bst = SongBST()
        self.player = MusicPlayer()
        self.current_node = None

        # UI setup
        self.create_widgets()
        self.load_songs()

    def create_widgets(self):
        # Title label
        tk.Label(
            self.root, text="Music Manager", font=("Segoe UI", 16, "bold"),
            fg="white", bg="#121212"
        ).pack(pady=10)

        # Playlist frame
        frame = tk.Frame(self.root, bg="#121212")
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            frame, bg="#1e1e1e", fg="white", font=("Consolas", 11),
            selectbackground="#0078D7", activestyle="none"
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#121212")
        btn_frame.pack(pady=15)

        style = {
            "width": 10,
            "font": ("Segoe UI", 10, "bold"),
            "bg": "#0078D7",
            "fg": "white"
        }

        tk.Button(btn_frame, text="▶ Play", command=self.play_selected, **style).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="⏸ Pause", command=self.pause_song, **style).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="⏹ Stop", command=self.stop_song, **style).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="⏵ Next", command=self.next_song, **style).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="⏴ Prev", command=self.prev_song, **style).grid(row=0, column=4, padx=5)

        # BST display frame
        bst_frame = tk.Frame(self.root, bg="#121212")
        bst_frame.pack(pady=5, fill="x")

        tk.Label(bst_frame, text="Sorted Playlist (A-Z)", fg="white", bg="#121212",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=5)

        self.bst_box = tk.Listbox(bst_frame, bg="#1e1e1e", fg="white", height=6)
        self.bst_box.pack(fill="x", padx=5)

        # Current song label
        self.status_label = tk.Label(
            self.root, text="No song playing", bg="#121212", fg="lightgray",
            font=("Segoe UI", 10)
        )
        self.status_label.pack(pady=10)

    def load_songs(self):
        if not os.path.exists(SONG_DIR):
            os.makedirs(SONG_DIR)

        self.playlist.load_from_folder(SONG_DIR)
        self.song_map.rebuild_from_playlist(self.playlist)

        # insert all playlist songs into BST
        cur = self.playlist.head
        while cur:
            self.bst.insert(cur.title)
            cur = cur.next

        self.update_listbox()
        self.update_bst_box()

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        cur = self.playlist.head
        while cur:
            self.listbox.insert(tk.END, cur.title)
            cur = cur.next
        if self.listbox.size() == 0:
            self.listbox.insert(tk.END, "No songs found in songs/ folder")

    def update_bst_box(self):
        self.bst_box.delete(0, tk.END)
        sorted_titles = self.bst.inorder()
        for title in sorted_titles:
            self.bst_box.insert(tk.END, title)

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


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicManagerGUI(root)
    root.mainloop()
