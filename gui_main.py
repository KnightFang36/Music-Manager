import sys, os, threading, time
from urllib.request import urlopen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, 
    QPushButton, QSlider, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap
from stack_queue import RecentlyPlayed
from player import MusicPlayer

SONG_DIR = "songs"
DEFAULT_COVER_URL = "https://i.pinimg.com/originals/48/71/8f/48718f3afca6b1b4296141d5cbd96619.jpg"

class SpotifyStyleGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Music Manager - PyQt6")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("background-color: #121212; color: white;")

        # Core modules
        self.playlist = Playlist()
        self.song_map = SongMap()
        self.history = RecentlyPlayed()
        self.heap = SongHeap()
        self.player = MusicPlayer()
        self.current_node = None
        self.playing = False

        self.setup_ui()
        self.load_songs()

    def setup_ui(self):
        # Main layout
        main_layout = QHBoxLayout(self)
        
        # Sidebar
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "background-color: #1e1e1e; selection-background-color: #FF4500;"
            "font-size: 14px;"
        )
        self.list_widget.setFixedWidth(250)
        main_layout.addWidget(self.list_widget)

        # Right main area
        right_layout = QVBoxLayout()

        # Album art placeholder - Load default cover
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(300, 300)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border: 2px solid #2c2c2c;")
        self.load_default_cover()
        right_layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Song title
        self.song_label = QLabel("No song playing")
        self.song_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.song_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar {background-color: #2c2c2c; border: none; height: 15px;}"
            "QProgressBar::chunk {background-color: #FF4500;}"
        )
        self.progress_bar.setMaximum(100)
        right_layout.addWidget(self.progress_bar)

        # Controls
        control_layout = QHBoxLayout()
        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.pause_btn = QPushButton("⏸")
        self.next_btn = QPushButton("⏭")
        for btn in [self.prev_btn, self.play_btn, self.pause_btn, self.next_btn]:
            btn.setStyleSheet("background-color: #FF4500; font-size: 18px; color: white; border-radius: 10px; padding:10px;")
            control_layout.addWidget(btn)
        right_layout.addLayout(control_layout)

        # Volume slider
        vol_layout = QHBoxLayout()
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setValue(80)
        self.vol_slider.setStyleSheet(
            "QSlider::groove:horizontal {background: #2c2c2c; height: 10px;}"
            "QSlider::handle:horizontal {background: #FF4500; width: 20px;}"
        )
        vol_layout.addWidget(QLabel("Volume"))
        vol_layout.addWidget(self.vol_slider)
        right_layout.addLayout(vol_layout)

        main_layout.addLayout(right_layout)

        # Connections
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.play_btn.clicked.connect(self.play_selected)
        self.pause_btn.clicked.connect(self.pause_song)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_btn.clicked.connect(self.prev_song)
        self.vol_slider.valueChanged.connect(self.set_volume)

        # Timer for progress bar
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(500)

    def load_default_cover(self):
        """Load the default album cover from URL"""
        try:
            print(f"Loading default cover from URL...")
            # Download image data
            with urlopen(DEFAULT_COVER_URL) as response:
                image_data = response.read()
            
            # Load into pixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                scaled_pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.SmoothTransformation)
                self.cover_label.setPixmap(scaled_pixmap)
                print("✓ Default cover loaded successfully!")
            else:
                print("✗ Failed to parse image data")
                self.set_fallback_cover()
        except Exception as e:
            print(f"✗ Failed to load image: {e}")
            self.set_fallback_cover()
    
    def set_fallback_cover(self):
        """Set a fallback black square if image doesn't load"""
        pixmap = QPixmap(300, 300)
        pixmap.fill(Qt.GlobalColor.darkGray)
        self.cover_label.setPixmap(pixmap)

    def load_songs(self):
        if not os.path.exists(SONG_DIR):
            os.makedirs(SONG_DIR)
        self.playlist.load_from_folder(SONG_DIR)
        self.song_map.rebuild_from_playlist(self.playlist)
        self.list_widget.clear()
        cur = self.playlist.head
        while cur:
            self.list_widget.addItem(cur.title)
            cur = cur.next

    def play_selected(self):
        item = self.list_widget.currentItem()
        if item is None: return
        node = self.song_map.search_song(item.text())
        if node:
            self.play_node(node)

    def play_node(self, node):
        self.current_node = node
        self.song_label.setText(f"🎶 {node.title}")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        self.playing = True

    def pause_song(self):
        self.player.pause()
        self.playing = False

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.play_node(self.current_node.next)

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.play_node(self.current_node.prev)

    def set_volume(self, val):
        self.player.set_volume(val / 100)

    def update_progress(self):
        if self.playing and self.player.is_playing():
            self.progress_bar.setValue((self.progress_bar.value() + 1) % 101)
        else:
            self.progress_bar.setValue(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = SpotifyStyleGUI()
    gui.show()
    sys.exit(app.exec())