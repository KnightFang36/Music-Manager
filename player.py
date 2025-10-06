
# --- pygame-based MusicPlayer backend ---
import os
import pygame
import threading
import time

class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.play_thread = None
        self.stop_event = threading.Event()
        self.paused = False
        self.current_path: str | None = None

    def _play_worker(self, path: str, start: float = 0.0):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(start=start)
            while not self.stop_event.is_set() and pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print("Playback error:", e)
        finally:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def play(self, path: str, start: float = 0.0) -> None:
        if not os.path.exists(path):
            print("File not found:", path)
            return
        self.stop()
        self.stop_event.clear()
        self.paused = False
        self.current_path = path
        self.play_thread = threading.Thread(target=self._play_worker, args=(path, start), daemon=True)
        self.play_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=0.5)
        self.play_thread = None
        self.stop_event.clear()
        self.paused = False

    def pause(self) -> None:
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass
        self.paused = True

    def resume(self) -> None:
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass
        self.paused = False

    def is_playing(self) -> bool:
        try:
            return pygame.mixer.music.get_busy()
        except Exception:
            return False

    def is_paused(self) -> bool:
        return self.paused

    def set_volume(self, vol: float) -> None:
        try:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
        except Exception:
            pass