# playlist_dll.py
# Doubly Linked List implementation for the playlist
import os
from typing import Optional, List, Tuple

class Node:
    def __init__(self, title: str, path: str):
        self.title = title
        self.path = path
        self.prev: Optional['Node'] = None
        self.next: Optional['Node'] = None

class Playlist:
    def __init__(self):
        self.head: Optional[Node] = None
        self.tail: Optional[Node] = None
        self.size = 0

    def insert_song_end(self, title: str, path: str) -> Node:
        node = Node(title, path)
        if not self.head:
            self.head = self.tail = node
        else:
            assert self.tail is not None
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        self.size += 1
        return node

    def delete_song_by_title(self, title: str) -> bool:
        cur = self.head
        while cur:
            if cur.title.lower() == title.lower():
                if cur.prev:
                    cur.prev.next = cur.next
                else:
                    self.head = cur.next
                if cur.next:
                    cur.next.prev = cur.prev
                else:
                    self.tail = cur.prev
                self.size -= 1
                return True
            cur = cur.next
        return False

    def find_node_by_title(self, title: str) -> Optional[Node]:
        cur = self.head
        while cur:
            if cur.title.lower() == title.lower():
                return cur
            cur = cur.next
        return None

    def to_list(self) -> List[Tuple[str, str]]:
        res = []
        cur = self.head
        while cur:
            res.append((cur.title, cur.path))
            cur = cur.next
        return res

    def display_playlist(self) -> None:
        if not self.head:
            print("No songs in playlist.")
            return
        print("\n📜 Playlist:")
        i = 1
        cur = self.head
        while cur:
            print(f"{i}. {cur.title}")
            cur = cur.next
            i += 1

    def shuffle_playlist(self) -> None:
        import random
        songs = self.to_list()
        random.shuffle(songs)
        self.head = self.tail = None
        self.size = 0
        for title, path in songs:
            self.insert_song_end(title, path)

    def load_from_folder(self, folder: str, limit: int = 50) -> None:
        # scans for mp3 files and inserts them
        if not os.path.exists(folder):
            os.makedirs(folder)
            return
        files = [f for f in os.listdir(folder) if f.lower().endswith('.mp3')]
        files = files[:limit]
        for f in files:
            title = os.path.splitext(f)[0]
            path = os.path.join(folder, f)
            self.insert_song_end(title, path)

    def __len__(self):
        return self.size
