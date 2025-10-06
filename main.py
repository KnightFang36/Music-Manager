# main.py
import os
import json
import shutil
from playlist_dll import Playlist
from hashmap import SongMap
from stack_queue import RecentlyPlayed, UpcomingSongs
from heap_bst import SongHeap, SongBST
from player import MusicPlayer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SONG_DIR = os.path.join(BASE_DIR, 'songs')
PLAY_COUNTS = os.path.join(DATA_DIR, 'play_counts.json')


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
        except Exception:
            pass


def save_play_counts(heap: SongHeap):
    try:
        with open(PLAY_COUNTS, 'w', encoding='utf-8') as f:
            json.dump(heap.counter, f, indent=2)
    except Exception as e:
        print('Could not save play counts:', e)


def init_music_manager():
    playlist = Playlist()
    song_map = SongMap()
    history = RecentlyPlayed(max_size=500)
    upcoming = UpcomingSongs(capacity=10)
    heap = SongHeap()
    bst = SongBST()
    player = MusicPlayer()

    playlist.load_from_folder(SONG_DIR)
    song_map.rebuild_from_playlist(playlist)

    load_play_counts(heap)
    return playlist, song_map, history, upcoming, heap, bst, player


def print_menu():
    print('\n🎵 MUSIC MANAGER — MENU')
    print('1. Show playlist')
    print('2. Play song (by number)')
    print('3. Play song (by title)')
    print('4. Pause / Resume / Stop')
    print('5. Next / Previous during playing')
    print('6. Add song to upcoming queue')
    print('7. Show upcoming')
    print('7.5 Play next from upcoming')
    print('8. Search')
    print('9. Shuffle playlist')
    print('10. Delete song from playlist')
    print('11. Add song (copy mp3 to songs/ folder)')
    print('12. Show recently played')
    print('13. Clear history')
    print('14. Top played')
    print('15. Save & Exit')


def main():
    ensure_dirs()
    playlist, song_map, history, upcoming, heap, bst, player = init_music_manager()
    current_node = None

    if len(playlist) == 0:
        print("No MP3 files found in 'songs/' folder. Add up to 50 .mp3 files and restart.")

    try:
        while True:
            print_menu()
            choice = input('Choose an option: ').strip()

            if choice == '1':
                playlist.display_playlist()

            elif choice == '2':
                playlist.display_playlist()
                idx = input('Enter number to play: ').strip()
                if not idx.isdigit():
                    print('Invalid number')
                    continue
                idx = int(idx)
                cur = playlist.head
                i = 1
                found = False
                while cur and i <= idx:
                    if i == idx:
                        found = True
                        break
                    cur = cur.next
                    i += 1
                if not found or cur is None:
                    print('Index out of range')
                    continue
                current_node = cur
                print(f"Now playing: {cur.title}")
                player.play(cur.path)
                history.push(cur.title)
                heap.add_play(cur.title)

            elif choice == '3':
                title = input('Enter song title: ').strip()
                node = song_map.search_song(title)
                if not node:
                    print('Song not found in playlist.')
                    continue
                current_node = node
                print(f"Now playing: {node.title}")
                player.play(node.path)
                history.push(node.title)
                heap.add_play(node.title)

            elif choice == '4':
                # Offer controls if a track is loaded (playing or paused)
                if current_node or player.is_playing() or player.is_paused():
                    sub = input('P=Pause, R=Resume, S=Stop: ').strip().lower()
                    if sub == 'p':
                        player.pause(); print('Paused')
                    elif sub == 'r':
                        player.resume(); print('Resumed')
                    elif sub == 's':
                        player.stop(); print('Stopped')
                    else:
                        print('Invalid')
                else:
                    print('No song is currently loaded.')

            elif choice == '5':
                if current_node is None:
                    print('No active song. Start playing first.')
                    continue
                ctrl = input('N=Next, P=Previous: ').strip().lower()
                if ctrl == 'n' and current_node.next:
                    current_node = current_node.next
                elif ctrl == 'p' and current_node.prev:
                    current_node = current_node.prev
                else:
                    print('No next/previous song available.')
                    continue
                print(f"Now playing: {current_node.title}")
                player.play(current_node.path)
                history.push(current_node.title)
                heap.add_play(current_node.title)

            elif choice == '6':
                playlist.display_playlist()
                title = input('Enter exact title to add to upcoming queue: ').strip()
                node = song_map.search_song(title)
                if not node:
                    print('Song not found.')
                    continue
                upcoming.enqueue(node.title)
                print(f'Enqueued {node.title} to upcoming')

            elif choice == '7':
                upcoming.show()

            elif choice == '7.5':
                title = upcoming.dequeue()
                if not title:
                    print('Upcoming queue is empty.')
                else:
                    node = song_map.search_song(title)
                    if not node:
                        print('Song not found in playlist.')
                    else:
                        current_node = node
                        print(f"Now playing: {node.title}")
                        player.play(node.path)
                        history.push(node.title)
                        heap.add_play(node.title)

            elif choice == '8':
                q = input('Search by substring: ').strip().lower()
                matches = []
                cur = playlist.head
                while cur:
                    if q in cur.title.lower():
                        matches.append(cur.title)
                    cur = cur.next
                if not matches:
                    print('No matches')
                else:
                    print('Matches:')
                    for i, t in enumerate(matches, 1):
                        print(f"{i}. {t}")

            elif choice == '9':
                playlist.shuffle_playlist()
                song_map.rebuild_from_playlist(playlist)
                current_node = playlist.head
                print('Playlist shuffled. Reset to first track.')

            elif choice == '10':
                playlist.display_playlist()
                title = input('Enter exact title to delete: ').strip()
                ok = playlist.delete_song_by_title(title)
                if ok:
                    song_map.remove_from_hash(title)
                    print('Deleted')
                else:
                    print('Not found')

            elif choice == '11':
                p = input('Enter full path to .mp3 (or leave blank to skip): ').strip()
                if not p:
                    continue
                if not os.path.exists(p) or not p.lower().endswith('.mp3'):
                    print('File not found or not an mp3')
                    continue
                dst = os.path.join(SONG_DIR, os.path.basename(p))
                shutil.copy2(p, dst)
                node = playlist.insert_song_end(os.path.splitext(os.path.basename(dst))[0], dst)
                song_map.insert_to_hash(node.title, node)
                bst.insert(node.title)
                print('Copied and added to playlist')

            elif choice == '12':
                history.show()

            elif choice == '13':
                confirm = input('Clear history? (y/N): ').strip().lower()
                if confirm == 'y':
                    history.clear(); print('History cleared')

            elif choice == '14':
                heap.show_top(10)

            elif choice == '15':
                print('Saving state...')
                save_play_counts(heap)
                player.stop()
                print('Bye!')
                break

            else:
                print('Invalid option')

    except KeyboardInterrupt:
        print('\nExiting...')
        save_play_counts(heap)
        player.stop()


if __name__ == "__main__":
    main()
