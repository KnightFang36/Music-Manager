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
        else:
            if node.right is None:
                node.right = Node(title)
            else:
                self._insert(node.right, title)
