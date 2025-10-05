import sys, os
from urllib.request import urlopen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, 
    QPushButton, QSlider, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap
from bst import BST
from stack_queue import RecentlyPlayed
from player import MusicPlayer


SONG_DIR = "songs"
DEFAULT_COVER_URL = "https://i.pinimg.com/originals/48/71/8f/48718f3afca6b1b4296141d5cbd96619.jpg"


class SpotifyStyleGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Music Manager - PyQt6")
        self.setGeometry(100, 100, 1400, 700)
        self.setStyleSheet("background-color: #121212; color: white;")

        # Core modules
        self.playlist = Playlist()
        self.song_map = SongMap()
        self.history = RecentlyPlayed()
        self.heap = SongHeap()
        self.bst = None  # BST for sorting
        self.player = MusicPlayer()
        self.current_node = None
        self.playing = False

        self.setup_ui()
        self.load_songs()
        self.update_top_played_ui()
        self.update_recently_played_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar_container = QWidget()
        sidebar_container.setStyleSheet("background-color: #1e1e1e;")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(15)

        # Playlist label & sorting toggle
        playlist_label = QLabel("Playlist", alignment=Qt.AlignmentFlag.AlignCenter)
        playlist_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        sidebar_layout.addWidget(playlist_label)

        self.sort_toggle = QCheckBox("Sort Alphabetically")
        self.sort_toggle.setStyleSheet("color: white; font-size: 13px;")
        self.sort_toggle.setFixedWidth(160)
        self.sort_toggle.stateChanged.connect(self.toggle_sorting)
        sidebar_layout.addWidget(self.sort_toggle)

        # Playlist QListWidget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget {background-color: #1e1e1e; selection-background-color: #FF4500;"
            "font-size: 14px; border: none; padding: 10px; outline: none; color: white;}"
            "QListWidget::item {padding: 8px; border-radius: 4px;}"
            "QListWidget::item:hover {background-color: #2a2a2a;}"
            "QListWidget::item:selected {background-color: #FF4500; color: white;}"
            "QListWidget::item:selected:active {background-color: #FF4500;}"
            "QListWidget::item:focus {outline: none; border: none;}"
        )
        self.list_widget.setFixedWidth(280)
        sidebar_layout.addWidget(self.list_widget)

        # Top Played songs
        top_label = QLabel("Top Played", alignment=Qt.AlignmentFlag.AlignCenter)
        top_label.setStyleSheet("font-weight: bold; font-size: 15px; margin-top: 10px;")
        sidebar_layout.addWidget(top_label)

        self.top_played_list = QListWidget()
        self.top_played_list.setStyleSheet("background-color: #1e1e1e; color: white; font-size: 13px;")
        self.top_played_list.setFixedWidth(280)
        sidebar_layout.addWidget(self.top_played_list)

        # Recently Played songs
        recent_label = QLabel("Recently Played", alignment=Qt.AlignmentFlag.AlignCenter)
        recent_label.setStyleSheet("font-weight: bold; font-size: 15px; margin-top: 10px;")
        sidebar_layout.addWidget(recent_label)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("background-color: #1e1e1e; color: white; font-size: 13px;")
        self.history_list.setFixedWidth(280)
        sidebar_layout.addWidget(self.history_list)

        main_layout.addWidget(sidebar_container)

        # Right main area
        right_container = QWidget()
        right_container.setStyleSheet("background-color: #121212;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(40, 40, 40, 40)
        right_layout.setSpacing(20)
        right_layout.addStretch(1)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(350, 350)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border: 2px solid #2c2c2c; border-radius: 8px;")
        self.load_default_cover()
        right_layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        right_layout.addSpacing(10)

        self.song_label = QLabel("No song playing")
        self.song_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setStyleSheet("color: white; padding: 10px;")
        right_layout.addWidget(self.song_label)

        right_layout.addSpacing(20)

        time_container = QWidget()
        time_container.setMaximumWidth(600)
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)

        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #b3b3b3; font-size: 13px;")
        self.current_time_label.setFixedWidth(45)
        time_layout.addWidget(self.current_time_label)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet(
            "QSlider::groove:horizontal {background: #4d4d4d; height: 5px; border-radius: 2px;}"
            "QSlider::handle:horizontal {background: white; width: 14px; height: 14px; border-radius: 7px; margin: -5px 0;}"
            "QSlider::sub-page:horizontal {background: #FF4500; border-radius: 2px;}"
        )
        self.progress_slider.setMaximum(100)
        time_layout.addWidget(self.progress_slider)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #b3b3b3; font-size: 13px;")
        self.total_time_label.setFixedWidth(45)
        self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        time_layout.addWidget(self.total_time_label)

        right_layout.addWidget(time_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        right_layout.addSpacing(15)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)

        self.prev_btn = QPushButton("◀◀")
        self.play_pause_btn = QPushButton("▶")
        self.next_btn = QPushButton("▶▶")

        side_btn_style = (
            "QPushButton {background-color: transparent; font-size: 20px; color: #b3b3b3; "
            "border: none; border-radius: 25px; padding: 15px; min-width: 50px; min-height: 50px; outline: none;}"
            "QPushButton:hover {color: white; background-color: #2a2a2a;}"
            "QPushButton:pressed {background-color: #1a1a1a;}"
            "QPushButton:focus {outline: none; border: none;}"
        )

        main_btn_style = (
            "QPushButton {background-color: white; font-size: 20px; color: #121212; "
            "border: none; border-radius: 25px; padding: 15px; min-width: 50px; min-height: 50px; outline: none;}"
            "QPushButton:hover {background-color: #f0f0f0;}"
            "QPushButton:pressed {background-color: #d0d0d0;}"
            "QPushButton:focus {outline: none; border: none;}"
        )

        self.prev_btn.setStyleSheet(side_btn_style)
        self.play_pause_btn.setStyleSheet(main_btn_style)
        self.next_btn.setStyleSheet(side_btn_style)

        self.prev_btn.setFixedSize(50, 50)
        self.play_pause_btn.setFixedSize(50, 50)
        self.next_btn.setFixedSize(50, 50)

        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.play_pause_btn)
        control_layout.addWidget(self.next_btn)

        right_layout.addLayout(control_layout)

        right_layout.addSpacing(20)

        vol_container = QWidget()
        vol_container.setMaximumWidth(400)
        vol_layout = QHBoxLayout(vol_container)
        vol_layout.setContentsMargins(0, 0, 0, 0)

        vol_label = QLabel("🔊 Volume")
        vol_label.setStyleSheet("color: #b3b3b3; font-size: 14px;")
        vol_label.setFixedWidth(80)
        vol_layout.addWidget(vol_label)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setValue(80)
        self.vol_slider.setStyleSheet(
            "QSlider::groove:horizontal {background: #4d4d4d; height: 5px; border-radius: 2px;}"
            "QSlider::handle:horizontal {background: #FF4500; width: 14px; height: 14px; border-radius: 7px; margin: -5px 0;}"
            "QSlider::sub-page:horizontal {background: #FF4500; border-radius: 2px;}"
        )
        vol_layout.addWidget(self.vol_slider)

        self.vol_percentage_label = QLabel("80%")
        self.vol_percentage_label.setStyleSheet("color: #b3b3b3; font-size: 14px;")
        self.vol_percentage_label.setFixedWidth(45)
        self.vol_percentage_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        vol_layout.addWidget(self.vol_percentage_label)

        right_layout.addWidget(vol_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        right_layout.addStretch(1)

        main_layout.addWidget(right_container)

        # Connections
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_btn.clicked.connect(self.prev_song)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)
        self.slider_being_dragged = False

    def load_default_cover(self):
        try:
            with urlopen(DEFAULT_COVER_URL) as response:
                image_data = response.read()
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                scaled_pixmap = pixmap.scaled(350, 350, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.cover_label.setPixmap(scaled_pixmap)
            else:
                self.set_fallback_cover()
        except Exception:
            self.set_fallback_cover()

    def set_fallback_cover(self):
        pixmap = QPixmap(350, 350)
        pixmap.fill(Qt.GlobalColor.darkGray)
        self.cover_label.setPixmap(pixmap)

    def load_songs(self):
        if not os.path.exists(SONG_DIR):
            os.makedirs(SONG_DIR)
        self.playlist.load_from_folder(SONG_DIR)
        self.song_map.rebuild_from_playlist(self.playlist)
        self.build_bst_from_playlist()
        self.update_playlist_display()

    def build_bst_from_playlist(self):
        self.bst = BST()
        cur = self.playlist.head
        while cur:
            self.bst.insert(cur.title)
            cur = cur.next

    def get_bst_sorted_titles(self):
        result = []

        def inorder(node):
            if node is None:
                return
            inorder(node.left)
            result.append(node.title)
            inorder(node.right)

        inorder(self.bst.root)
        return result

    def update_playlist_display(self):
        self.list_widget.clear()
        if self.sort_toggle.isChecked():
            sorted_titles = self.get_bst_sorted_titles()
            for title in sorted_titles:
                self.list_widget.addItem(title)
        else:
            cur = self.playlist.head
            while cur:
                self.list_widget.addItem(cur.title)
                cur = cur.next

    def toggle_sorting(self, state):
        self.update_playlist_display()

    def play_selected(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        node = self.song_map.search_song(item.text())
        if node:
            self.play_node(node)

    def toggle_play_pause(self):
        if self.playing:
            self.pause_song()
        else:
            if self.current_node:
                self.play_node(self.current_node)
            else:
                self.play_selected()

    def play_node(self, node):
        self.current_node = node
        self.song_label.setText(f"🎶 {node.title}")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        self.playing = True
        self.play_pause_btn.setText("||")

        try:
            import pygame
            sound = pygame.mixer.Sound(node.path)
            duration = sound.get_length()
            self.progress_slider.setMaximum(int(duration))
            self.total_time_label.setText(self.format_time(duration))
        except:
            self.progress_slider.setMaximum(100)
            self.total_time_label.setText("0:00")

        self.update_top_played_ui()
        self.update_recently_played_ui()

    def pause_song(self):
        self.player.pause()
        self.playing = False
        self.play_pause_btn.setText("▶")

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.play_node(self.current_node.next)

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.play_node(self.current_node.prev)

    def set_volume(self, val):
        self.player.set_volume(val / 100)
        self.vol_percentage_label.setText(f"{val}%")

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def slider_pressed(self):
        self.slider_being_dragged = True

    def slider_released(self):
        self.slider_being_dragged = False
        if self.playing:
            new_pos = self.progress_slider.value()
            try:
                pass
            except:
                pass

    def update_progress(self):
        if self.playing and self.player.is_playing() and not self.slider_being_dragged:
            try:
                import pygame
                pos = pygame.mixer.music.get_pos() / 1000.0
                if pos >= 0:
                    self.progress_slider.setValue(int(pos))
                    self.current_time_label.setText(self.format_time(pos))
                if not pygame.mixer.music.get_busy() and self.playing:
                    self.playing = False
                    self.play_pause_btn.setText("▶")
                    if self.current_node and self.current_node.next:
                        self.next_song()
            except:
                pass
        elif not self.playing:
            self.progress_slider.setValue(0)
            self.current_time_label.setText("0:00")

    def update_top_played_ui(self):
        self.top_played_list.clear()
        top_songs = self.heap.get_top(10)
        for title, count in top_songs:
            self.top_played_list.addItem(f"{title} - Plays: {count}")

    def update_recently_played_ui(self):
        self.history_list.clear()
        recent_songs = self.history.get_all()
        for title in recent_songs:
            self.history_list.addItem(title)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = SpotifyStyleGUI()
    gui.show()
    sys.exit(app.exec())
