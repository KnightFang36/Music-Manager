# MuzicSpot Music Player

A modern, feature-rich music player built with PyQt6 and pygame. This project combines a sleek UI with efficient data structures to create a responsive music management experience.

## Features

- **Clean, modern UI** with album art display and player controls
- **Smart library management** with alphabetical sorting and search
- **Play queue** for planning your listening session
- **Recently played history** that remembers your favorites
- **Most played tracking** to highlight your top songs
- **Smooth seeking** with click-to-position and double-click-to-drag functionality
- **Responsive design** that scales well with different window sizes

## Getting Started

### Prerequisites

- Python 3.8+ (tested with Python 3.13)
- PyQt6
- pygame
- mutagen (for audio metadata)
- pillow (for image processing)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/KnightFang36/Music-Manager.git
   cd Music-Manager
   ```

2. Set up a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install PyQt6 pygame mutagen pillow
   ```

4. Run the player:
   ```bash
   python gui_main.py
   ```

### Adding Music

Place MP3 files in the `songs` directory (created automatically when you first run the app). The app will automatically find and load them the next time you start it.## How It Works (DSA Implementation)

This project was developed as part of a Data Structures and Algorithms course, with specific focus on practical applications of DSA concepts. Here's how different data structures power the app:

### Doubly Linked List (Playlist)
The backbone of our music library is a doubly linked list, which lets us navigate forwards and backwards through songs with O(1) complexity. This gives us instant access to the next or previous song without any performance penalty.

```python
# Moving to next song (simplified example)
if self.current_node and self.current_node.next:
    self.play_node(self.current_node.next)
```

### HashMap (SongMap)
Searching for a song by title happens in constant time (O(1)) thanks to our custom HashMap implementation. This maintains responsive performance even with large music libraries.

```python
# Finding and playing a song by title (simplified)
node = self.song_map.search_song(title)
if node:
    self.play_node(node)
```

### Stack (RecentlyPlayed)
Your listening history is maintained in a stack data structure, naturally tracking songs in the order they were played (LIFO - Last In, First Out). This makes it easy to see your recent listening patterns.

### Circular Queue (UpcomingSongs)
The "Play Next" queue is implemented as a circular queue, efficiently managing the upcoming songs with O(1) enqueue and dequeue operations. This ensures quick access to the next song in the queue.

### Binary Heap (SongHeap)
Top played songs are tracked using a binary heap, allowing us to maintain and update play counts with O(log n) efficiency. This makes retrieving your most played songs nearly instantaneous.

### Binary Search Tree (BST)
When you toggle alphabetical sorting, a BST provides an efficient O(log n) approach to keeping your songs alphabetically ordered. This improves navigation and browsing experience.

## UI Walkthrough

### Main Interface
- **Left Panel**: Your song library and upcoming queue
- **Center**: Album art and current song information
- **Right Panels**: Top played and recently played lists
- **Bottom**: Playback controls and timeline

### Controls
- **Play/Pause**: Toggle playback of current song
- **Next/Previous**: Navigate between songs
- **Timeline**: Click anywhere to seek to that position
- **Timeline (Double-Click)**: Double-click near the handle to enable drag mode
- **Volume Slider**: Adjust playback volume
- **Autoplay Queue**: Toggle automatic playback of queued songs

## Known Issues

- Some MP3 files might not display album art if it's stored in an uncommon format
- Seeking in very long audio files (>1 hour) might have slight timing imprecision
- Playlist state isn't preserved between sessions (planned for future update)

## Future Plans

- Multiple playlist support
- Audio visualizations
- Equalizer functionality
- Cross-platform packaging for easier distribution
- Integration with online music metadata sources

## Contributing

Noticed a bug or have an idea? Feel free to open an issue or submit a pull request!

1. Fork the repo
2. Create a feature branch (`git checkout -b cool-new-feature`)
3. Commit your changes (`git commit -am 'Added a cool feature'`)
4. Push to the branch (`git push origin cool-new-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) and [pygame](https://www.pygame.org/)
- Album art retrieval via remote URLs
- Audio metadata processing with [mutagen](https://mutagen.readthedocs.io/)

---

*Built as a Data Structures & Algorithms project, winter semester 2025*