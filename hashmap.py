# hashmap.py
# Simple hash map wrapper for song title lookup (case-insensitive)
from typing import Optional

class SongMap:
    def __init__(self):
        # map lowercase title -> Node (from playlist_dll)
        self.map = {}

    def insert_to_hash(self, title: str, node) -> None:
        self.map[title.lower()] = node

    def remove_from_hash(self, title: str) -> None:
        self.map.pop(title.lower(), None)

    def search_song(self, title: str):
        return self.map.get(title.lower())

    def rebuild_from_playlist(self, playlist) -> None:
        # playlist: Playlist instance
        self.map.clear()
        cur = playlist.head
        while cur:
            self.insert_to_hash(cur.title, cur)
            cur = cur.next
