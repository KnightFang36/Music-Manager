import heapq

class SongHeap:
    def __init__(self):
        # Map to track play counts: {title: count}
        self.count_map = {}
        # Heap as list of (-count, title) for max-heap behavior
        self.heap_list = []

    def add_play(self, title):
        if title in self.count_map:
            self.count_map[title] += 1
        else:
            self.count_map[title] = 1
        self._rebuild_heap()

    def _rebuild_heap(self):
        # Rebuild the heap from count_map items
        self.heap_list = [(-count, title) for title, count in self.count_map.items()]
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
