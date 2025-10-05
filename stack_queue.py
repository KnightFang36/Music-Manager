# stack_queue.py
# RecentlyPlayed (Stack) and UpcomingSongs (Circular Queue with dynamic resize)
from collections import deque
from typing import Optional

class RecentlyPlayed:
    def __init__(self):
        self.stack = []

    def push(self, title):
        self.stack.append(title)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None

    def get_all(self):
        # Return list of songs most recent first
        return self.stack[::-1]

    def clear(self):
        self.stack.clear()

    def __len__(self):
        return len(self.stack)


class UpcomingSongs:
    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.queue = [None] * capacity
        self.front = 0
        self.rear = -1
        self.size = 0

    def is_full(self) -> bool:
        return self.size == self.capacity

    def is_empty(self) -> bool:
        return self.size == 0

    def _resize(self) -> None:
        new_cap = self.capacity * 2
        new_q = [None] * new_cap
        for i in range(self.size):
            new_q[i] = self.queue[(self.front + i) % self.capacity]
        self.queue = new_q
        self.front = 0
        self.rear = self.size - 1
        self.capacity = new_cap
        print(f"🔄 Upcoming queue resized -> {self.capacity}")

    def enqueue(self, title: str) -> None:
        if self.is_full():
            self._resize()
        self.rear = (self.rear + 1) % self.capacity
        self.queue[self.rear] = title
        self.size += 1

    def dequeue(self) -> Optional[str]:
        if self.is_empty():
            return None
        val = self.queue[self.front]
        self.front = (self.front + 1) % self.capacity
        self.size -= 1
        return val

    def show(self) -> None:
        if self.is_empty():
            print("No upcoming songs.")
            return
        print("\n🎶 Upcoming Songs:")
        for i in range(self.size):
            print(f"{i+1}. {self.queue[(self.front + i) % self.capacity]}")
