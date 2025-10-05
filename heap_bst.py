# heap_bst.py
# Most-played counting (Counter/heap) and a simple BST for alphabetical sort

from collections import Counter
import heapq


class SongHeap:
    def __init__(self):
        self.counter = Counter()

    def add_play(self, title: str) -> None:
        self.counter[title] += 1

    def top_n(self, n: int = 5):
        return self.counter.most_common(n)

    def show_top(self, n: int = 5) -> None:
        top = self.top_n(n)
        if not top:
            print("No play history yet.")
            return

        print("\nTop played songs:")
        for i, (t, c) in enumerate(top, 1):
            print(f"{i}. {t} — {c} plays")


class BSTNode:
    def __init__(self, title: str):
        self.title = title
        self.left = None
        self.right = None


class SongBST:
    def __init__(self):
        self.root = None

    def insert(self, title: str) -> None:
        self.root = self._insert(self.root, title)

    def _insert(self, node, title: str):
        if node is None:
            return BSTNode(title)

        if title.lower() < node.title.lower():
            node.left = self._insert(node.left, title)
        elif title.lower() > node.title.lower():
            node.right = self._insert(node.right, title)
        return node

    def inorder(self):
        res = []
        self._inorder(self.root, res)
        return res

    def _inorder(self, node, res):
        if not node:
            return
        self._inorder(node.left, res)
        res.append(node.title)
        self._inorder(node.right, res)

    def show_sorted(self):
        arr = self.inorder()
        if not arr:
            print("No songs to show.")
            return

        print("\nSorted Playlist (BST inorder):")
        for i, t in enumerate(arr, 1):
            print(f"{i}. {t}")
