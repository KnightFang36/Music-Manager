import heapq

class SongHeap:
    def __init__(self):
        # Map to track play counts: {title: count}
        # Named 'counter' to match main.py expectations
        self.counter = {}
        # Backward-compat alias if other modules reference count_map
        self.count_map = self.counter
        # Heap as list of (-count, title) for max-heap behavior
        self.heap_list = []

    def add_play(self, title):
        # Increment play count and rebuild heap
        if title in self.counter:
            self.counter[title] += 1
        else:
            self.counter[title] = 1
        self._rebuild_heap()

    def _rebuild_heap(self):
        # Rebuild the heap from current counters
        self.heap_list = [(-count, title) for title, count in self.counter.items()]
        heapq.heapify(self.heap_list)

    def get_top(self, n=10):
        # Return top n songs as list of (title, count) tuples without modifying original heap
        heap_copy = self.heap_list[:]
        heapq.heapify(heap_copy)
        top = []
        for _ in range(min(n, len(heap_copy))):
            count_neg, title = heapq.heappop(heap_copy)
            top.append((title, -count_neg))
        return top

    def show_top(self, n=10):
        # Pretty-print top N songs (used by console app)
        top = self.get_top(n)
        if not top:
            print("No plays recorded yet.")
            return
        print("\n🎯 Top Played Songs:")
        for i, (title, cnt) in enumerate(top, 1):
            print(f"{i}. {title} — {cnt} plays")


class Node:
    def __init__(self, title):
        self.title = title
        self.left = None
        self.right = None


class BST:
    def __init__(self):
        self.root = None

    def insert(self, title):
        if self.root is None:
            self.root = Node(title)
        else:
            self._insert(self.root, title)

    def _insert(self, node, title):
        if title < node.title:
            if node.left is None:
                node.left = Node(title)
            else:
                self._insert(node.left, title)
        elif title > node.title:
            if node.right is None:
                node.right = Node(title)
            else:
                self._insert(node.right, title)
        # Duplicate titles are ignored, no insertion

    def inorder(self):
        # Return list of titles in sorted order
        result = []

        def _inorder(node):
            if node:
                _inorder(node.left)
                result.append(node.title)
                _inorder(node.right)

        _inorder(self.root)
        return result

# Alias class name expected by main.py
class SongBST(BST):
    pass
