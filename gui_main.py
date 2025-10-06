import sys, os, json
from urllib.request import urlopen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QPushButton, QSlider, QCheckBox, QLineEdit, QFrame, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor
from playlist_dll import Playlist
from hashmap import SongMap
from heap_bst import SongHeap
from bst import BST
from stack_queue import RecentlyPlayed, UpcomingSongs
from player import MusicPlayer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SONG_DIR = os.path.join(BASE_DIR, "songs")
PLAY_COUNTS = os.path.join(DATA_DIR, 'play_counts.json')
RECENT_HISTORY = os.path.join(DATA_DIR, 'recently_played.json')
DEFAULT_COVER_URL = "https://i.pinimg.com/originals/48/71/8f/48718f3afca6b1b4296141d5cbd96619.jpg"

# ----------------- Utility Functions -----------------
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SONG_DIR, exist_ok=True)

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

def save_play_counts(heap: SongHeap):
    try:
        ensure_dirs()
        with open(PLAY_COUNTS, 'w', encoding='utf-8') as f:
            json.dump(heap.counter, f, indent=2)
    except Exception as e:
        print('Could not save play counts:', e)

def load_recent_history(history: RecentlyPlayed):
    if os.path.exists(RECENT_HISTORY):
        try:
            with open(RECENT_HISTORY, 'r', encoding='utf-8') as f:
                data = json.load(f)
                history.stack = data.get('history', [])
        except Exception as e:
            print('Could not load recently played history:', e)

def save_recent_history(history: RecentlyPlayed):
    try:
        ensure_dirs()
        with open(RECENT_HISTORY, 'w', encoding='utf-8') as f:
            json.dump({'history': history.stack}, f, indent=2)
    except Exception as e:
        print('Could not save recently played history:', e)

# ----------------- Main GUI Class -----------------
class ModernMusicPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Player")
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
                color: #ffffff;
                font-family: 'Segoe UI', 'San Francisco', 'Arial';
            }
        """)
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

        # Load data
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

        # ----------------- Left Sidebar -----------------
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a1a, stop:1 #0f0f0f);
                border-right: 1px solid #2a2a2a;
            }
        """)
        
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 30, 20, 30)
        side_layout.setSpacing(20)

        # App Title
        app_title = QLabel("♪ MUSIC PLAYER")
        app_title.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #FF6B35;
            letter-spacing: 2px;
            padding: 10px 0;
        """)
        app_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        side_layout.addWidget(app_title)

        # Divider
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet("background-color: #2a2a2a; max-height: 1px;")
        side_layout.addWidget(divider1)

        # Playlist Section
        pl_header = QHBoxLayout()
        pl_label = QLabel("YOUR LIBRARY")
        pl_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #888888;
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
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #FF6B35;
                border: 1px solid #FF6B35;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #FF6B35;
            }
        """)
        self.sort_toggle.stateChanged.connect(self.update_playlist_display)
        side_layout.addWidget(self.sort_toggle)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search songs...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 2px solid #2a2a2a;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #FF6B35;
                background-color: #202020;
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
                color: #cccccc;
                padding: 12px 16px;
                border-radius: 8px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B35, stop:1 #FF8C42);
                color: #ffffff;
                font-weight: 600;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #1a1a1a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #FF6B35;
            }
        """)
        side_layout.addWidget(self.list_widget)

        # Enqueue Button
        self.enqueue_btn = QPushButton("ADD TO QUEUE")
        self.enqueue_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B35, stop:1 #FF8C42);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF7B45, stop:1 #FF9C52);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E55B25, stop:1 #E57C32);
            }
        """)
        self.enqueue_btn.clicked.connect(self.enqueue_selected)
        side_layout.addWidget(self.enqueue_btn)

        # Divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet("background-color: #2a2a2a; max-height: 1px; margin: 10px 0;")
        side_layout.addWidget(divider2)

        # Upcoming Queue
        up_label = QLabel("UP NEXT")
        up_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #888888;
            letter-spacing: 1px;
        """)
        side_layout.addWidget(up_label)

        self.upcoming_list = QListWidget()
        self.upcoming_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item {
                color: #999999;
                padding: 10px 12px;
                border-radius: 6px;
                margin: 1px 0;
            }
            QListWidget::item:hover {
                background-color: #1a1a1a;
                color: #ffffff;
            }
        """)
        side_layout.addWidget(self.upcoming_list)

        # Play Next Button
        self.play_next_upcoming_btn = QPushButton("▶ PLAY NEXT")
        self.play_next_upcoming_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #FF6B35;
            }
        """)
        self.play_next_upcoming_btn.clicked.connect(self.play_next_from_upcoming)
        side_layout.addWidget(self.play_next_upcoming_btn)

        main_layout.addWidget(sidebar)

        # ----------------- Center Content -----------------
        center_container = QFrame()
        center_container.setStyleSheet("background-color: #0a0a0a;")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(60, 40, 60, 40)
        center_layout.setSpacing(0)

        # Main Content Area
        content_area = QHBoxLayout()
        content_area.setSpacing(60)

        # Left: Album Cover Section
        album_section = QVBoxLayout()
        album_section.setAlignment(Qt.AlignmentFlag.AlignCenter)
        album_section.setSpacing(30)

        # Album Cover
        cover_container = QFrame()
        cover_container.setFixedSize(420, 420)
        cover_container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 12px;
                border: 1px solid #2a2a2a;
            }
        """)
        cover_layout = QVBoxLayout(cover_container)
        cover_layout.setContentsMargins(10, 10, 10, 10)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(400, 400)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            border-radius: 8px;
            background-color: #0f0f0f;
        """)
        self.load_default_cover()
        cover_layout.addWidget(self.cover_label)
        
        album_section.addWidget(cover_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Song Info
        self.song_label = QLabel("No song playing")
        self.song_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setStyleSheet("""
            color: #ffffff;
            padding: 20px;
            background-color: transparent;
        """)
        self.song_label.setWordWrap(True)
        album_section.addWidget(self.song_label)

        content_area.addLayout(album_section)

        # Right: Stats Section
        stats_section = QVBoxLayout()
        stats_section.setAlignment(Qt.AlignmentFlag.AlignTop)
        stats_section.setSpacing(25)

        # Top Played Card
        top_card_frame = QFrame()
        top_card_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a1a, stop:1 #151515);
                border: 1px solid #2a2a2a;
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
            color: #FF6B35;
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
                color: #cccccc;
                padding: 10px;
                border-radius: 6px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 107, 53, 0.1);
                color: #FF6B35;
            }
        """)
        top_card_layout.addWidget(self.top_played_list)
        stats_section.addWidget(top_card_frame)

        # Recently Played Card
        recent_card_frame = QFrame()
        recent_card_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a1a, stop:1 #151515);
                border: 1px solid #2a2a2a;
                border-radius: 12px;
            }
        """)
        recent_card_frame.setFixedWidth(400)
        recent_card_frame.setFixedHeight(320)
        
        recent_card_layout = QVBoxLayout(recent_card_frame)
        recent_card_layout.setContentsMargins(20, 20, 20, 20)
        recent_card_layout.setSpacing(10)
        
        recent_header = QLabel("🕐 RECENTLY PLAYED")
        recent_header.setStyleSheet("""
            font-size: 14px;
            font-weight: 700;
            color: #FF6B35;
            letter-spacing: 1px;
        """)
        recent_card_layout.addWidget(recent_header)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                color: #cccccc;
                padding: 10px;
                border-radius: 6px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 107, 53, 0.1);
                color: #FF6B35;
            }
        """)
        recent_card_layout.addWidget(self.history_list)
        stats_section.addWidget(recent_card_frame)

        content_area.addLayout(stats_section)
        center_layout.addLayout(content_area)

        center_layout.addStretch()

        # ----------------- Bottom Player Bar -----------------
        player_bar = QFrame()
        player_bar.setFixedHeight(140)
        player_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a1a, stop:1 #0f0f0f);
                border-top: 1px solid #2a2a2a;
            }
        """)
        player_layout = QVBoxLayout(player_bar)
        player_layout.setContentsMargins(40, 15, 40, 15)
        player_layout.setSpacing(10)

        # Progress Bar with Time
        progress_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #888888; font-size: 12px; min-width: 40px;")
        progress_layout.addWidget(self.current_time_label)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2a2a2a;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B35, stop:1 #FF8C42);
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
                background: #FF6B35;
            }
        """)
        self.progress_slider.sliderPressed.connect(lambda: setattr(self, 'slider_being_dragged', True))
        self.progress_slider.sliderReleased.connect(lambda: setattr(self, 'slider_being_dragged', False))
        progress_layout.addWidget(self.progress_slider)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #888888; font-size: 12px; min-width: 40px;")
        self.total_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_layout.addWidget(self.total_time_label)
        player_layout.addLayout(progress_layout)

        # Controls Row
        controls_row = QHBoxLayout()
        
        # Left: Volume
        vol_layout = QHBoxLayout()
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 18px;")
        vol_layout.addWidget(vol_icon)
        
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setFixedWidth(120)
        self.vol_slider.setValue(80)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2a2a2a;
                height: 5px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #FF6B35;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        self.vol_slider.valueChanged.connect(self.set_volume)
        vol_layout.addWidget(self.vol_slider)
        
        self.vol_percentage_label = QLabel("80%")
        self.vol_percentage_label.setStyleSheet("color: #888888; font-size: 12px; min-width: 35px;")
        vol_layout.addWidget(self.vol_percentage_label)
        controls_row.addLayout(vol_layout)

        controls_row.addStretch()

        # Center: Playback Controls
        playback_controls = QHBoxLayout()
        playback_controls.setSpacing(15)

        btn_style = """
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                font-size: 22px;
                padding: 10px;
                border-radius: 25px;
                min-width: 50px;
                min-height: 50px;
            }
            QPushButton:hover {
                color: #FF6B35;
                background-color: transparent;
            }
            QPushButton:pressed {
                color: #FF8C42;
                background-color: transparent;
            }
        """

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setStyleSheet(btn_style)
        self.prev_btn.clicked.connect(self.prev_song)
        playback_controls.addWidget(self.prev_btn)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B35, stop:1 #FF8C42);
                color: white;
                border: none;
                font-size: 24px;
                padding: 12px;
                border-radius: 30px;
                min-width: 60px;
                min-height: 60px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF7B45, stop:1 #FF9C52);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E55B25, stop:1 #E57C32);
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        playback_controls.addWidget(self.play_pause_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setStyleSheet(btn_style)
        self.next_btn.clicked.connect(self.next_song)
        playback_controls.addWidget(self.next_btn)

        controls_row.addLayout(playback_controls)
        controls_row.addStretch()

        player_layout.addLayout(controls_row)

        center_layout.addWidget(player_bar)
        main_layout.addWidget(center_container)

        # ----------------- Connections -----------------
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.upcoming_list.itemDoubleClicked.connect(self.enqueue_selected_from_upcoming)
        self.history_list.itemDoubleClicked.connect(self.play_selected_recently_played)
        self.top_played_list.itemDoubleClicked.connect(self.play_selected_top_played)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)

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

    # ----------------- Cover Art -----------------
    def load_default_cover(self):
        try:
            with urlopen(DEFAULT_COVER_URL) as response:
                data = response.read()
            pix = QPixmap()
            pix.loadFromData(data)
            pix = pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        except:
            pix = QPixmap(400, 400)
            pix.fill(QColor("#0f0f0f"))
            self.cover_label.setPixmap(pix)

    def try_set_cover(self, path):
        try:
            from mutagen.id3 import ID3
            tags = ID3(path)
            apics = tags.getall('APIC')
            if apics:
                data = apics[0].data
                pix = QPixmap()
                pix.loadFromData(data)
                pix = pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.cover_label.setPixmap(pix)
                return True
        except:
            pass
        return False

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
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        save_play_counts(self.heap)
        save_recent_history(self.history)
        self.playing = True
        self.play_pause_btn.setText("⏸")
        if not self.try_set_cover(node.path):
            pass
        # Duration
        try:
            from mutagen import File as MutagenFile
            mf = MutagenFile(node.path)
            dur = getattr(mf.info, 'length', 0)
            self.progress_slider.setMaximum(int(dur))
            self.total_time_label.setText(f"{int(dur//60)}:{int(dur%60):02d}")
        except:
            self.progress_slider.setMaximum(100)
            self.total_time_label.setText("0:00")
        self.update_top_played_ui()
        self.update_recently_played_ui()
        self.update_upcoming_ui()

    def toggle_play_pause(self):
        if self.playing:
            self.player.pause()
            self.playing = False
            self.play_pause_btn.setText("▶")
        else:
            if self.current_node:
                self.play_node(self.current_node)
            else:
                self.play_selected()

    def next_song(self):
        if self.current_node and self.current_node.next:
            self.play_node(self.current_node.next)

    def prev_song(self):
        if self.current_node and self.current_node.prev:
            self.play_node(self.current_node.prev)

    def set_volume(self, val):
        self.player.set_volume(val / 100)
        self.vol_percentage_label.setText(f"{val}%")

    # ----------------- Progress -----------------
    def update_progress(self):
        if self.playing and self.player.is_playing() and not self.slider_being_dragged:
            try:
                import pygame
                pos = pygame.mixer.music.get_pos() / 1000
                self.progress_slider.setValue(int(pos))
                self.current_time_label.setText(f"{int(pos//60)}:{int(pos%60):02d}")
                if not pygame.mixer.music.get_busy() and self.playing:
                    self.playing = False
                    self.play_pause_btn.setText("▶")
                    self.next_song()
            except:
                pass

    # ----------------- Top & Recent -----------------
    def update_top_played_ui(self):
        self.top_played_list.clear()
        top = self.heap.get_top(10)
        for t, c in top:
            item = QListWidgetItem(f"{t} · {c} plays")
            self.top_played_list.addItem(item)

    def update_recently_played_ui(self):
        self.history_list.clear()
        for t in self.history.get_all():
            self.history_list.addItem(t)

    # ----------------- Upcoming Queue -----------------
    def update_upcoming_ui(self):
        self.upcoming_list.clear()
        for i in range(self.upcoming.size):
            idx = (self.upcoming.front + i) % self.upcoming.capacity
            t = self.upcoming.queue[idx]
            if t:
                self.upcoming_list.addItem(t)

    def add_to_upcoming(self, title):
        self.upcoming.enqueue(title)
        self.update_upcoming_ui()

    def play_next_from_upcoming(self):
        title = self.upcoming.dequeue()
        if not title:
            self.song_label.setText("No upcoming songs")
            return
        node = self.song_map.search_song(title)
        if node:
            self.play_node(node)
        self.update_upcoming_ui()

# ----------------- Run -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ModernMusicPlayer()
    gui.show()
    sys.exit(app.exec())