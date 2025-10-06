import sys, os, json
from urllib.request import urlopen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QPushButton, QSlider, QCheckBox, QLineEdit, QFrame, QListWidgetItem, QStyle
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QColor
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap
from bst import BST
from stack_queue import RecentlyPlayed, UpcomingSongs
from player import MusicPlayer
import pygame
import time

# Suppress all Qt warnings (optional)
os.environ["QT_LOGGING_RULES"] = "qt*=false"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SONG_DIR = os.path.join(BASE_DIR, "songs")
PLAY_COUNTS = os.path.join(DATA_DIR, 'play_counts.json')
RECENT_HISTORY = os.path.join(DATA_DIR, 'recently_played.json')
DEFAULT_COVER_URL = "https://i.redd.it/wo1p6792qi371.png"
DEFAULT_COVER_PATH = os.path.join(DATA_DIR, 'default_cover.png')

# ----------------- Utility Functions -----------------
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SONG_DIR, exist_ok=True)

def cache_default_cover():
    """Cache the default cover image locally to avoid repeated network requests."""
    if not os.path.exists(DEFAULT_COVER_PATH):
        try:
            with urlopen(DEFAULT_COVER_URL) as response:
                data = response.read()
            with open(DEFAULT_COVER_PATH, 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"Failed to cache default cover: {e}")

def load_play_counts(heap: SongHeap):
    if os.path.exists(PLAY_COUNTS):
        try:
            with open(PLAY_COUNTS, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for title, cnt in data.items():
                    heap.counter[title] = cnt
            heap._rebuild_heap()
        except Exception as e:
            print('Could not load play counts:', e)

def save_play_counts(heap: SongHeap, force=False):
    """Save play counts with debouncing to reduce I/O frequency."""
    if hasattr(save_play_counts, 'last_save') and not force:
        if time.time() - save_play_counts.last_save < 5:  # Debounce for 5 seconds
            return
    try:
        ensure_dirs()
        with open(PLAY_COUNTS, 'w', encoding='utf-8') as f:
            json.dump(heap.counter, f, indent=2)
        save_play_counts.last_save = time.time()
    except Exception as e:
        print('Could not save play counts:', e)
save_play_counts.last_save = 0

def load_recent_history(history: RecentlyPlayed):
    if os.path.exists(RECENT_HISTORY):
        try:
            with open(RECENT_HISTORY, 'r', encoding='utf-8') as f:
                data = json.load(f)
                history.stack = data.get('history', [])
        except Exception as e:
            print('Could not load recently played history:', e)

def save_recent_history(history: RecentlyPlayed, force=False):
    """Save recent history with debouncing to reduce I/O frequency."""
    if hasattr(save_recent_history, 'last_save') and not force:
        if time.time() - save_recent_history.last_save < 5:  # Debounce for 5 seconds
            return
    try:
        ensure_dirs()
        with open(RECENT_HISTORY, 'w', encoding='utf-8') as f:
            json.dump({'history': history.stack}, f, indent=2)
        save_recent_history.last_save = time.time()
    except Exception as e:
        print('Could not save recently played history:', e)
save_recent_history.last_save = 0

# ----------------- Simplified Slider Class -----------------
class ClickableSlider(QSlider):
    positionChanged = pyqtSignal(int)
    def __init__(self, orientation):
        super().__init__(orientation)
        self.user_is_setting = False
        self.drag_enabled = False  # Only allow dragging after double-click
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value):
        if self.user_is_setting:
            self.positionChanged.emit(value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.drag_enabled:
                self.user_is_setting = True
                value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), int(event.position().x()), self.width())
                self.setValue(value)
                self.positionChanged.emit(value)
                return
            else:
                self.user_is_setting = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_enabled and self.user_is_setting:
            value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), int(event.position().x()), self.width())
            self.setValue(value)
            self.positionChanged.emit(value)
            super().mouseMoveEvent(event)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.user_is_setting = False
            if self.drag_enabled:
                self.drag_enabled = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle_x = QStyle.sliderPositionFromValue(self.minimum(), self.maximum(), self.value(), self.width())
            click_x = int(event.position().x())
            if abs(click_x - handle_x) <= 12:
                self.drag_enabled = True
                super().mouseDoubleClickEvent(event)
            else:
                value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), click_x, self.width())
                self.setValue(value)
                self.positionChanged.emit(value)
        else:
            super().mouseDoubleClickEvent(event)

# ----------------- Main GUI Class -----------------
class ModernMusicPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Player")
        
        # Set minimum size based on screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        min_width = min(1550, screen.width() - 20)
        min_height = min(1096, screen.height() - 50)
        self.setMinimumSize(min_width, min_height)
        self.showMaximized()

        # Core modules
        self.playlist = Playlist()
        self.song_map = SongMap()
        self.history = RecentlyPlayed(max_size=20)
        self.heap = SongHeap()
        self.bst = None
        self.player = MusicPlayer()
        self.current_node = None
        self.playing = False
        self.upcoming = UpcomingSongs()
        self.slider_being_dragged = False
        self.current_position = 0
        self.autoplay_enabled = True
        self.song_duration = 0
        self.play_start_offset = 0
        self.previous_volume = 80  # Store previous volume for mute/unmute

        # Cache for UI optimizations
        self.last_top_played = []
        self.last_recently_played = []
        self.last_upcoming = []

        # Timer for UI sync
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(200)

        # Load data
        cache_default_cover()
        load_play_counts(self.heap)
        load_recent_history(self.history)

        # Setup UI
        self.setup_ui()
        self.load_songs()
        self.update_top_played_ui()
        self.update_recently_played_ui()
        self.update_upcoming_ui()

    # ----------------- UI Setup -----------------
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15, 15, 15, 0.85), stop:1 rgba(10, 10, 10, 0.85));
                border-right: 1px solid rgba(60, 60, 60, 0.5);
            }
        """)
        
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 30, 20, 30)
        side_layout.setSpacing(20)

        # App Title
        app_title = QLabel("🎸 MuzicSpot")
        app_title.setStyleSheet("""
            font-size: 26px;
            font-weight: 700;
            color: #D94F00;
            letter-spacing: 2px;
            padding: 10px 0;
        """)
        app_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        side_layout.addWidget(app_title)

        # Divider
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet("background-color: rgba(60, 60, 60, 0.5); max-height: 1px;")
        side_layout.addWidget(divider1)

        # Playlist Section
        pl_header = QHBoxLayout()
        pl_label = QLabel("YOUR LIBRARY")
        pl_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #999999;
            letter-spacing: 1px;
        """)
        pl_header.addWidget(pl_label)
        pl_header.addStretch()
        side_layout.addLayout(pl_header)

        # Sort Toggle
        self.sort_toggle = QCheckBox("Alphabetical")
        self.sort_toggle.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: rgba(60, 60, 60, 0.7);
                border: 1px solid rgba(80, 80, 80, 0.5);
            }
            QCheckBox::indicator:checked {
                background-color: #D94F00;
                border: 1px solid #D94F00;
            }
        """)
        self.sort_toggle.stateChanged.connect(self.update_playlist_display)
        side_layout.addWidget(self.sort_toggle)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search songs...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(10, 10, 10, 0.8);
                color: #ffffff;
                border: 1px solid rgba(60, 60, 60, 0.5);
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #D94F00;
                background-color: rgba(15, 15, 15, 0.8);
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
        self.search_input.textChanged.connect(self.update_playlist_display)
        side_layout.addWidget(self.search_input)

        # Playlist List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                font-size: 14px;
                padding: 5px;
            }
            QListWidget::item {
                color: #dddddd;
                padding: 12px 16px;
                border-radius: 8px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                color: #000000;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B03C00, stop:1 #C74300);
                color: #000000;
                font-weight: 600;
            }
        """)
        side_layout.addWidget(self.list_widget, stretch=3)

        # Enqueue Button
        self.enqueue_btn = QPushButton("ADD TO QUEUE")
        self.enqueue_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E55B00, stop:1 #F57600);
            }
        """)
        self.enqueue_btn.clicked.connect(self.enqueue_selected)
        side_layout.addWidget(self.enqueue_btn)

        # Upcoming Queue
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet("background-color: rgba(60, 60, 60, 0.5); max-height: 1px; margin: 10px 0;")
        side_layout.addWidget(divider2)

        up_label = QLabel("UP NEXT")
        up_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #999999;
            letter-spacing: 1px;
        """)
        side_layout.addWidget(up_label)

        self.upcoming_list = QListWidget()
        self.upcoming_list.setMaximumHeight(100)
        self.upcoming_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item {
                color: #aaaaaa;
                padding: 10px 12px;
                border-radius: 6px;
                margin: 1px 0;
            }
            QListWidget::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                color: #000000;
            }
        """)
        side_layout.addWidget(self.upcoming_list, stretch=1)

        self.play_next_upcoming_btn = QPushButton("▶ PLAY NEXT")
        self.play_next_upcoming_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        self.play_next_upcoming_btn.clicked.connect(self.play_next_from_upcoming)
        side_layout.addWidget(self.play_next_upcoming_btn)

        self.autoplay_checkbox = QCheckBox("🔄 Autoplay Queue")
        self.autoplay_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
                font-weight: 500;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #D94F00;
                border-radius: 4px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #D94F00;
                border: 2px solid #D94F00;
            }
        """)
        self.autoplay_checkbox.setChecked(True)
        side_layout.addWidget(self.autoplay_checkbox)

        main_layout.addWidget(sidebar)

        # Center Content
        center_container = QFrame()
        center_container.setStyleSheet("background-color: #0A0A0A;")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(60, 40, 60, 40)
        center_layout.setSpacing(0)

        # Main Content Area
        content_area = QHBoxLayout()
        content_area.setSpacing(60)

        # Album Cover Section (centered and fixed size)
        album_section = QVBoxLayout()
        album_section.setAlignment(Qt.AlignmentFlag.AlignCenter)
        album_section.setSpacing(20)

        cover_container = QFrame()
        cover_container.setFixedSize(650, 750)
        cover_container.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 10, 10, 0.8);
                border-radius: 12px;
            }
        """)
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(10, 10, 10, 10)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(630, 730)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            border-radius: 8px;
            background-color: #0A0A0A;
        """)
        self.load_default_cover()
        cover_layout.addWidget(self.cover_label)
        
        album_section.addWidget(cover_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Song Info
        self.song_label = QLabel("No song playing")
        self.song_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Normal))
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setStyleSheet("""
            color: #ffffff;
            padding: 20px;
            background-color: transparent;
        """)
        self.song_label.setWordWrap(True)
        album_section.addWidget(self.song_label)

        content_area.addLayout(album_section)

        # Stats Section (Top Played + Recently Played)
        stats_section = QVBoxLayout()
        stats_section.setAlignment(Qt.AlignmentFlag.AlignTop)
        stats_section.setSpacing(25)

        # Top Played Card
        top_card_frame = QFrame()
        top_card_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 20, 20, 0.85), stop:1 rgba(10, 10, 10, 0.85));
                border: 1px solid rgba(60, 60, 60, 0.5);
                border-radius: 12px;
            }
        """)
        top_card_frame.setFixedWidth(400)
        top_card_frame.setFixedHeight(320)
        
        top_card_layout = QVBoxLayout(top_card_frame)
        top_card_layout.setContentsMargins(20, 20, 20, 20)
        top_card_layout.setSpacing(10)
        
        top_header = QLabel("🔥 TOP PLAYED")
        top_header.setStyleSheet("""
            font-size: 14px;
            font-weight: 700;
            color: #D94F00;
            letter-spacing: 1px;
        """)
        top_card_layout.addWidget(top_header)
        
        self.top_played_list = QListWidget()
        self.top_played_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                color: #dddddd;
                padding: 10px;
                border-radius: 6px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                color: #000000;
            }
        """)
        top_card_layout.addWidget(self.top_played_list)
        stats_section.addWidget(top_card_frame)

        # Recently Played Card
        recent_card_frame = QFrame()
        recent_card_frame.setStyleSheet(top_card_frame.styleSheet())
        recent_card_frame.setFixedWidth(400)
        recent_card_frame.setFixedHeight(320)
        
        recent_card_layout = QVBoxLayout(recent_card_frame)
        recent_card_layout.setContentsMargins(20, 20, 20, 20)
        recent_card_layout.setSpacing(10)
        
        recent_header = QLabel("🕐 RECENTLY PLAYED")
        recent_header.setStyleSheet("""
            font-size: 14px;
            font-weight: 700;
            color: #D94F00;
            letter-spacing: 1px;
        """)
        recent_card_layout.addWidget(recent_header)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(self.top_played_list.styleSheet())
        recent_card_layout.addWidget(self.history_list)
        stats_section.addWidget(recent_card_frame)

        content_area.addLayout(stats_section)
        center_layout.addLayout(content_area)

        # Bottom player bar
        player_bar = QFrame()
        player_bar.setFixedHeight(140)
        player_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15, 15, 15, 0.85), stop:1 rgba(10, 10, 10, 0.85));
                border-top: 1px solid rgba(60, 60, 60, 0.5);
            }
        """)
        player_layout = QVBoxLayout(player_bar)
        player_layout.setContentsMargins(40, 15, 40, 15)
        player_layout.setSpacing(10)

        # Progress row
        progress_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #999999; font-size: 12px; min-width: 40px;")
        progress_layout.addWidget(self.current_time_label)

        self.progress_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(60, 60, 60, 0.7);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #D94F00;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.progress_slider.positionChanged.connect(self.slider_position_changed)
        progress_layout.addWidget(self.progress_slider)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #999999; font-size: 12px; min-width: 40px;")
        self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_layout.addWidget(self.total_time_label)
        player_layout.addLayout(progress_layout)

        # Playback and Volume Controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(20)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        playback_frame = QFrame()
        playback_frame.setFixedWidth(200)
        playback_layout = QHBoxLayout(playback_frame)
        playback_layout.setSpacing(15)
        playback_layout.setContentsMargins(0, 0, 0, 0)
        playback_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        btn_style = """
            QPushButton {
                background-color: transparent;
                color: #dddddd;
                border: none;
                font-size: 18px;
                padding: 10px;
                border-radius: 25px;
                min-width: 40px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: transparent;
                color: #D94F00;
            }
            QPushButton:pressed {
                background-color: transparent;
                color: #C74300;
            }
        """

        self.prev_btn = QPushButton("<<")
        self.prev_btn.setStyleSheet(btn_style)
        self.prev_btn.clicked.connect(self.prev_song)
        playback_layout.addWidget(self.prev_btn)

        self.play_pause_btn = QPushButton("|> ")
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #000000;
                border: none;
                font-size: 18px;
                padding: 10px;
                border-radius: 25px;
                min-width: 50px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #000000;
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        playback_layout.addWidget(self.play_pause_btn)

        self.next_btn = QPushButton(">>")
        self.next_btn.setStyleSheet(btn_style)
        self.next_btn.clicked.connect(self.next_song)
        playback_layout.addWidget(self.next_btn)

        controls_row.addWidget(playback_frame)

        # Volume Control
        volume_frame = QFrame()
        volume_frame.setFixedWidth(350)
        vol_layout = QHBoxLayout(volume_frame)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        vol_layout.setSpacing(10)

        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setStyleSheet(btn_style)
        self.mute_btn.clicked.connect(self.toggle_mute)
        vol_layout.addWidget(self.mute_btn)

        self.vol_down_btn = QPushButton("−")
        self.vol_down_btn.setStyleSheet(btn_style)
        self.vol_down_btn.clicked.connect(self.volume_down)
        vol_layout.addWidget(self.vol_down_btn)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setFixedWidth(150)
        self.vol_slider.setValue(80)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(60, 60, 60, 0.7);
                height: 5px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D94F00, stop:1 #E56A00);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #D94F00;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #D94F00;
            }
        """)
        self.vol_slider.valueChanged.connect(self.set_volume)
        vol_layout.addWidget(self.vol_slider)

        self.vol_up_btn = QPushButton("+")
        self.vol_up_btn.setStyleSheet(btn_style)
        self.vol_up_btn.clicked.connect(self.volume_up)
        vol_layout.addWidget(self.vol_up_btn)

        self.vol_percentage_label = QLabel("80%")
        self.vol_percentage_label.setStyleSheet("color: #999999; font-size: 12px; min-width: 35px;")
        vol_layout.addWidget(self.vol_percentage_label)
        
        controls_row.addLayout(vol_layout)
        player_layout.addLayout(controls_row)

        center_layout.addWidget(player_bar)
        main_layout.addWidget(center_container)

        # Connections
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.upcoming_list.itemDoubleClicked.connect(self.enqueue_selected_from_upcoming)
        self.history_list.itemDoubleClicked.connect(self.play_selected_recently_played)
        self.top_played_list.itemDoubleClicked.connect(self.play_selected_top_played)

    # ----------------- Load Songs -----------------
    def load_songs(self):
        ensure_dirs()
        self.playlist.load_from_folder(SONG_DIR)
        self.song_map.rebuild_from_playlist(self.playlist)
        self.build_bst_from_playlist()
        self.update_playlist_display()

    # ----------------- BST Sorting -----------------
    def build_bst_from_playlist(self):
        self.bst = BST()
        cur = self.playlist.head
        while cur:
            self.bst.insert(cur.title)
            cur = cur.next

    def get_bst_sorted_titles(self):
        result = []
        def inorder(node):
            if not node:
                return
            inorder(node.left)
            result.append(node.title)
            inorder(node.right)
        inorder(self.bst.root)
        return result

    # ----------------- Playlist Display -----------------
    def update_playlist_display(self):
        self.list_widget.clear()
        filter_text = self.search_input.text().strip().lower() if self.search_input else ""
        if self.sort_toggle.isChecked():
            sorted_titles = self.get_bst_sorted_titles()
            for title in sorted_titles:
                if not filter_text or filter_text in title.lower():
                    self.list_widget.addItem(title)
        else:
            cur = self.playlist.head
            while cur:
                if not filter_text or filter_text in cur.title.lower():
                    self.list_widget.addItem(cur.title)
                cur = cur.next

    # ----------------- Cover Art (DEFAULT ONLY) -----------------
    def load_default_cover(self):
        try:
            pix = QPixmap()
            if os.path.exists(DEFAULT_COVER_PATH):
                pix.load(DEFAULT_COVER_PATH)
            else:
                with urlopen(DEFAULT_COVER_URL) as response:
                    data = response.read()
                pix.loadFromData(data)
                with open(DEFAULT_COVER_PATH, 'wb') as f:
                    f.write(data)
            pix = pix.scaled(630, 730, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        except Exception as e:
            print(f"Error loading default cover: {e}")
            pix = QPixmap(630, 730)
            pix.fill(QColor("#0A0A0A"))
            self.cover_label.setPixmap(pix)

    def try_set_cover(self, path):
        """
        Simplified behavior per your request:
        - ALWAYS use the default cover.
        - Do not attempt to read embedded APIC frames from each song (avoids NoneType errors).
        """
        self.load_default_cover()
        return True

    # ----------------- Playback -----------------
    def play_selected(self):
        item = self.list_widget.currentItem()
        if not item: return
        node = self.song_map.search_song(item.text())
        if node:
            self.play_node(node)

    def play_selected_recently_played(self, item):
        if not item: return
        node = self.song_map.search_song(item.text())
        if node:
            self.play_node(node)

    def play_selected_top_played(self, item):
        if not item: return
        title = item.text().split(" ·")[0].strip()
        node = self.song_map.search_song(title)
        if node:
            self.play_node(node)

    def enqueue_selected(self):
        item = self.list_widget.currentItem()
        if item: self.add_to_upcoming(item.text())

    def enqueue_selected_from_upcoming(self, item):
        self.play_next_from_upcoming()

    def play_node(self, node):
        self.current_node = node
        self.song_label.setText(f"🎵 {node.title}")
        self.current_position = 0
        self.play_start_offset = 0
        self.slider_being_dragged = False
        self.playing = True
        self.play_pause_btn.setText("||")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        save_play_counts(self.heap)
        save_recent_history(self.history)
        # Always load default cover (no per-song reading)
        self.load_default_cover()
        # Try to read duration (mutagen) but don't crash if unavailable
        try:
            from mutagen import File as MutagenFile
            mf = MutagenFile(node.path)
            dur = int(getattr(mf.info, 'length', 0))
            self.song_duration = dur
        except Exception:
            self.song_duration = 0
        self.progress_slider.setMaximum(max(self.song_duration, 1))
        self.progress_slider.setValue(0)
        self.total_time_label.setText(self.format_time(self.song_duration))
        self.current_time_label.setText("0:00")
        self.update_top_played_ui()
        self.update_recently_played_ui()
        self.update_upcoming_ui()
        # Highlight the current song in the playlist
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() == node.title:
                self.list_widget.setCurrentItem(item)
                self.list_widget.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)
                break

    def toggle_play_pause(self):
        if self.playing:
            self.player.pause()
            self.playing = False
            self.play_pause_btn.setText("|> ")
        else:
            if self.current_node:
                if self.player.is_paused():
                    self.player.resume()
                    self.playing = True
                    self.play_pause_btn.setText("||")
                else:
                    self.play_node(self.current_node)
            else:
                self.play_selected()

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.play_node(self.current_node.next)
        else:
            self.playing = False
            self.play_pause_btn.setText("|> ")

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.play_node(self.current_node.prev)

    def set_volume(self, val):
        self.player.set_volume(val / 100)
        self.vol_percentage_label.setText(f"{val}%")
        self.previous_volume = val if val > 0 else self.previous_volume
        self.mute_btn.setText("🔇" if val == 0 else "🔊")

    def toggle_mute(self):
        current_volume = self.vol_slider.value()
        if current_volume == 0:
            self.vol_slider.setValue(self.previous_volume)
        else:
            self.previous_volume = current_volume
            self.vol_slider.setValue(0)

    def volume_up(self):
        current_volume = self.vol_slider.value()
        new_volume = min(current_volume + 5, 100)
        self.vol_slider.setValue(new_volume)

    def volume_down(self):
        current_volume = self.vol_slider.value()
        new_volume = max(current_volume - 5, 0)
        self.vol_slider.setValue(new_volume)

    # ----------------- Progress -----------------
    def update_progress(self):
        if not self.playing:
            return
        try:
            if not self.slider_being_dragged:
                pos = pygame.mixer.music.get_pos() // 1000
                if pos < 0:
                    pos = 0
                absolute_pos = self.play_start_offset + pos
                self.current_position = absolute_pos
                self.progress_slider.blockSignals(True)
                self.progress_slider.setValue(absolute_pos)
                self.progress_slider.blockSignals(False)
                self.current_time_label.setText(self.format_time(absolute_pos))
            if self.song_duration > 0 and self.current_position >= self.song_duration - 1:
                self.playing = False
                self.play_pause_btn.setText("|> ")
                if self.autoplay_checkbox.isChecked() and self.upcoming.size > 0:
                    self.play_next_from_upcoming()
                else:
                    self.next_song()
        except Exception as e:
            # Keep errors visible in console but avoid crashing UI
            print(f"Error in update_progress: {e}")

    # ----------------- Top & Recent -----------------
    def update_top_played_ui(self):
        top = self.heap.get_top(10)
        if top != self.last_top_played:
            self.top_played_list.clear()
            for t, c in top:
                item = QListWidgetItem(f"{t} · {c} plays")
                self.top_played_list.addItem(item)
            self.last_top_played = top

    def update_recently_played_ui(self):
        recent = self.history.get_all()
        if recent != self.last_recently_played:
            self.history_list.clear()
            for t in recent:
                self.history_list.addItem(t)
            self.last_recently_played = recent

    # ----------------- Upcoming Queue -----------------
    def update_upcoming_ui(self):
        upcoming = [self.upcoming.queue[(self.upcoming.front + i) % self.upcoming.capacity] for i in range(self.upcoming.size)]
        if upcoming != self.last_upcoming:
            self.upcoming_list.clear()
            for t in upcoming:
                if t:
                    self.upcoming_list.addItem(t)
            self.last_upcoming = upcoming

    def add_to_upcoming(self, title):
        self.upcoming.enqueue(title)
        self.update_upcoming_ui()

    def play_next_from_upcoming(self):
        self.slider_being_dragged = False
        title = self.upcoming.dequeue()
        if not title:
            self.song_label.setText("No upcoming songs")
            return
        node = self.song_map.search_song(title)
        if node:
            self.play_node(node)
        self.update_upcoming_ui()

    # ----------------- Time Formatting -----------------
    def format_time(self, seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"

    # ----------------- Slider Handlers -----------------
    def slider_position_changed(self, position: int):
        self.current_time_label.setText(self.format_time(position))
        if not self.slider_being_dragged and self.current_node and self.playing:
            self.seek_to(position)

    def slider_pressed(self):
        self.slider_being_dragged = True

    def slider_released(self):
        self.slider_being_dragged = False
        if self.current_node and self.playing:
            new_pos = self.progress_slider.value()
            self.seek_to(new_pos)

    def seek_to(self, position: int):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.current_node.path)
            self.play_start_offset = int(position)
            pygame.mixer.music.play(start=float(position))
            self.current_position = int(position)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(self.current_position)
            self.progress_slider.blockSignals(False)
            self.current_time_label.setText(self.format_time(self.current_position))
        except Exception as e:
            print(f"Seek error: {e}")

# ----------------- Run -----------------
if __name__ == "__main__":
    # initialize pygame mixer (safe to call even if not used immediately)
    try:
        pygame.mixer.init()
    except Exception:
        # If pygame fails to initialize, player.play/is_playing behavior may be affected.
        print("Warning: pygame mixer failed to initialize; audio playback may not work.")

    app = QApplication(sys.argv)
    gui = ModernMusicPlayer()
    gui.show()
    sys.exit(app.exec())