import sys, os, json
from urllib.request import urlopen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel,
    QPushButton, QSlider, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap
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
class SpotifyStyleGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Music Manager")
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet("background-color: #121212; color: white;")
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
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # ----------------- Left Sidebar -----------------
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("background-color: #1e1e1e;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10,10,10,10)
        side_layout.setSpacing(15)

        # Playlist label & sorting
        pl_label = QLabel("Playlist", alignment=Qt.AlignmentFlag.AlignCenter)
        pl_label.setStyleSheet("font-weight:bold;font-size:15px;")
        side_layout.addWidget(pl_label)

        self.sort_toggle = QCheckBox("Sort Alphabetically")
        self.sort_toggle.setStyleSheet("color:white; font-size:13px;")
        self.sort_toggle.stateChanged.connect(self.update_playlist_display)
        side_layout.addWidget(self.sort_toggle)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title...")
        self.search_input.setStyleSheet(
            "background-color:#1e1e1e;color:white;border:1px solid #2c2c2c;padding:6px;border-radius:4px;")
        self.search_input.textChanged.connect(self.update_playlist_display)
        side_layout.addWidget(self.search_input)

        # Playlist list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget {background-color:#1e1e1e;color:white;font-size:14px;border:none;}"
            "QListWidget::item:hover {background-color:#2a2a2a;}"
            "QListWidget::item:selected {background-color:#FF4500;color:white;}")
        side_layout.addWidget(self.list_widget)

        # Enqueue button
        self.enqueue_btn = QPushButton("Enqueue Selected")
        self.enqueue_btn.setStyleSheet("background-color:#FF4500;color:white;font-size:13px;border-radius:6px;padding:6px;")
        self.enqueue_btn.clicked.connect(self.enqueue_selected)
        side_layout.addWidget(self.enqueue_btn)

        # Upcoming Queue
        up_label = QLabel("Upcoming Queue", alignment=Qt.AlignmentFlag.AlignCenter)
        up_label.setStyleSheet("font-weight:bold;font-size:15px;margin-top:10px;")
        side_layout.addWidget(up_label)

        self.upcoming_list = QListWidget()
        self.upcoming_list.setStyleSheet("background-color:#1e1e1e;color:white;font-size:13px;")
        side_layout.addWidget(self.upcoming_list)

        # Play next from upcoming
        self.play_next_upcoming_btn = QPushButton("Play Next from Upcoming")
        self.play_next_upcoming_btn.setStyleSheet("background-color:#FF4500;color:white;font-size:13px;border-radius:6px;padding:6px;")
        self.play_next_upcoming_btn.clicked.connect(self.play_next_from_upcoming)
        side_layout.addWidget(self.play_next_upcoming_btn)

        main_layout.addWidget(sidebar)

        # ----------------- Center & Right -----------------
        center_container = QWidget()
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(40,40,40,40)
        center_layout.setSpacing(40)

        # Album Cover & controls container
        album_widget = QWidget()
        album_widget.setFixedWidth(450)  # fixed width
        album_container = QVBoxLayout(album_widget)
        album_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(400,400)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border-radius:8px; border:2px solid #2c2c2c;")
        self.load_default_cover()
        album_container.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.song_label = QLabel("No song playing")
        self.song_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setStyleSheet("color:white;padding:10px;")
        album_container.addWidget(self.song_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress slider
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color:#b3b3b3;")
        time_layout.addWidget(self.current_time_label)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet(
            "QSlider::groove:horizontal{background:#4d4d4d;height:5px;border-radius:2px;}"
            "QSlider::handle:horizontal{background:white;width:14px;height:14px;border-radius:7px;margin:-5px 0;}"
            "QSlider::sub-page:horizontal{background:#FF4500;border-radius:2px;}")
        time_layout.addWidget(self.progress_slider)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color:#b3b3b3;")
        time_layout.addWidget(self.total_time_label)
        album_container.addLayout(time_layout)

        # Controls
        controls = QHBoxLayout()
        btn_style = ("QPushButton {background-color:transparent;color:#b3b3b3;"
                     "border:none;font-size:20px;padding:15px;border-radius:25px;}"
                     "QPushButton:hover{color:white;background-color:#2a2a2a;}")
        self.prev_btn = QPushButton("◀◀")
        self.prev_btn.setStyleSheet(btn_style)
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setStyleSheet(
            "QPushButton {background-color:white;color:#121212;border:none;font-size:20px;padding:15px;border-radius:25px;}"
            "QPushButton:hover{background-color:#f0f0f0;}")
        self.next_btn = QPushButton("▶▶")
        self.next_btn.setStyleSheet(btn_style)

        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_pause_btn)
        controls.addWidget(self.next_btn)
        album_container.addLayout(controls)

        # Volume
        vol_layout = QHBoxLayout()
        vol_label = QLabel("🔊 Volume")
        vol_label.setStyleSheet("color:#b3b3b3;font-size:14px;")
        vol_layout.addWidget(vol_label)
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setValue(80)
        self.vol_slider.setStyleSheet(
            "QSlider::groove:horizontal{background:#4d4d4d;height:5px;border-radius:2px;}"
            "QSlider::handle:horizontal{background:#FF4500;width:14px;height:14px;border-radius:7px;margin:-5px 0;}"
            "QSlider::sub-page:horizontal{background:#FF4500;border-radius:2px;}")
        vol_layout.addWidget(self.vol_slider)
        self.vol_percentage_label = QLabel("80%")
        self.vol_percentage_label.setStyleSheet("color:#b3b3b3;font-size:14px;")
        vol_layout.addWidget(self.vol_percentage_label)
        album_container.addLayout(vol_layout)

        center_layout.addWidget(album_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Right lists container
        right_widget = QWidget()
        right_widget.setFixedWidth(450)  # same width for symmetry
        right_lists = QVBoxLayout(right_widget)
        right_lists.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_label = QLabel("Top Played", alignment=Qt.AlignmentFlag.AlignCenter)
        top_label.setStyleSheet("font-weight:bold;font-size:15px;")
        right_lists.addWidget(top_label)

        self.top_played_list = QListWidget()
        self.top_played_list.setStyleSheet("background-color:#121212;color:white;font-size:13px;")
        right_lists.addWidget(self.top_played_list)

        recent_label = QLabel("Recently Played", alignment=Qt.AlignmentFlag.AlignCenter)
        recent_label.setStyleSheet("font-weight:bold;font-size:15px;margin-top:10px;")
        right_lists.addWidget(recent_label)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("background-color:#121212;color:white;font-size:13px;")
        right_lists.addWidget(self.history_list)

        center_layout.addWidget(right_widget)
        main_layout.addWidget(center_container)

        # ----------------- Connections -----------------
        self.list_widget.itemDoubleClicked.connect(self.play_selected)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.next_btn.clicked.connect(self.next_song)
        self.prev_btn.clicked.connect(self.prev_song)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.upcoming_list.itemDoubleClicked.connect(self.enqueue_selected_from_upcoming)
        self.history_list.itemDoubleClicked.connect(self.play_selected_recently_played)
        self.top_played_list.itemDoubleClicked.connect(self.play_selected_top_played)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)
        self.slider_being_dragged = False

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
            pix = pix.scaled(400,400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        except:
            pix = QPixmap(400,400)
            pix.fill(Qt.GlobalColor.darkGray)
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
                pix = pix.scaled(400,400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        title = item.text().split(" - Plays:")[0].strip()
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
        self.song_label.setText(f"🎶 {node.title}")
        self.player.play(node.path)
        self.history.push(node.title)
        self.heap.add_play(node.title)
        save_play_counts(self.heap)
        save_recent_history(self.history)
        self.playing = True
        self.play_pause_btn.setText("||")
        if not self.try_set_cover(node.path):
            pass
        # Duration
        try:
            from mutagen import File as MutagenFile
            mf = MutagenFile(node.path)
            dur = getattr(mf.info,'length',0)
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
            self.playing=False
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

    def set_volume(self,val):
        self.player.set_volume(val/100)
        self.vol_percentage_label.setText(f"{val}%")

    # ----------------- Progress -----------------
    def update_progress(self):
        if self.playing and self.player.is_playing() and not self.slider_being_dragged:
            try:
                import pygame
                pos = pygame.mixer.music.get_pos()/1000
                self.progress_slider.setValue(int(pos))
                self.current_time_label.setText(f"{int(pos//60)}:{int(pos%60):02d}")
                if not pygame.mixer.music.get_busy() and self.playing:
                    self.playing=False
                    self.play_pause_btn.setText("▶")
                    self.next_song()
            except: pass

    # ----------------- Top & Recent -----------------
    def update_top_played_ui(self):
        self.top_played_list.clear()
        top = self.heap.get_top(10)
        for t,c in top:
            self.top_played_list.addItem(f"{t} - Plays: {c}")

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
            if t: self.upcoming_list.addItem(t)

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
    gui = SpotifyStyleGUI()
    gui.show()
    sys.exit(app.exec())
