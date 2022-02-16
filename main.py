from __future__ import unicode_literals

import threading
import sqlite3
import time
import yaml
import PySimpleGUI as sg
import re, requests, subprocess, urllib.parse, urllib.request, os
import youtube_dl
from bs4 import BeautifulSoup
from pydub import AudioSegment, playback
from pydub.playback import play
global window
queue = []
with open("config.yml", 'r') as yaml_read:
    config = yaml.safe_load(yaml_read)


class ytdlProgress(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

def ytdl_progress_hook(d):
    if "_percent_str" in d:
        window['task'].update(f'Downloading: {d["_percent_str"]} complete...')
    elif d['status'] == 'finished':
        window['task'].update('Done downloading, now converting to mp3...')


def add_to_playlist(song, playlist, window):
    window['task'].update(f'Adding `{song}` to `{playlist}`')
    query_string = urllib.parse.urlencode({"search_query": song})
    formatUrl = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
    search_results = re.findall(r"watch\?v=(\S{11})", formatUrl.read().decode())
    clip = requests.get("https://www.youtube.com/watch?v=" + "{}".format(search_results[0]))
    video_url = "https://www.youtube.com/watch?v=" + "{}".format(search_results[0])
    video_info = youtube_dl.YoutubeDL().extract_info(
        url=video_url, download=False
    )
    filename = f"{video_info['title']}.{video_info['ext']}"
    mp3_filename = f"{video_info['title']}.mp3"
    con = sqlite3.connect('playlists.db')
    db = con.cursor()
    db.execute(f'CREATE TABLE IF NOT EXISTS {playlist} ("song"  TEXT, "url"  TEXT, "filename"  TEXT)')
    db.execute(f'INSERT INTO "{playlist}" (song, url, filename) VALUES ("{song}", "{video_url}", "{mp3_filename}")')
    con.commit()
    con.close()
    window.write_event_value('-THREAD-', f'Added `{song}` to `{playlist}`.')
    window['task'].update(f'Added `{song}` to `{playlist}`.')
    time.sleep(2)
    window['task'].update("Ready.")


def remove_from_playlist(song, playlist, window):
    query_string = urllib.parse.urlencode({"search_query": song})
    formatUrl = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
    search_results = re.findall(r"watch\?v=(\S{11})", formatUrl.read().decode())
    clip = requests.get("https://www.youtube.com/watch?v=" + "{}".format(search_results[0]))
    video_url = "https://www.youtube.com/watch?v=" + "{}".format(search_results[0])
    con = sqlite3.connect('playlists.db')
    db = con.cursor()
    db.execute(f'DELETE FROM "{playlist}" WHERE url = "{video_url}"')
    con.commit()
    con.close()
    window.write_event_value('-THREAD-', f'Removed `{song}` from `{playlist}`.')
    window['task'].update(f'Removed `{song}` from `{playlist}`.')
    time.sleep(2)
    window['task'].update("Ready.")


def play_playlist(playlist, window):
    global queue
    con = sqlite3.connect('playlists.db')
    db = con.cursor()
    filenames = db.execute(f'SELECT filename FROM {playlist}')
    filenames = filenames.fetchall()

    list(filenames)
    for i in filenames:
        i = str(i)
        i = i.strip("(,')")
        if os.path.exists(f"files/{i}"):
            print(f"{i} exists")
            queue.append(i)
        else:
            print(f"{i} doesn't exist, downloading now!")
            one_to_download = db.execute(f'SELECT url FROM {playlist} WHERE filename = "{i}"')
            one_to_download = db.fetchone()
            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'logger': ytdlProgress(),
                'progress_hooks': [ytdl_progress_hook],
                'keepvideo': False,
                'outtmpl': i,
            }
            with youtube_dl.YoutubeDL(options) as ydl:
                ydl.download(one_to_download)

            if not os.path.exists("files"):
                os.makedirs("files")
            window.write_event_value('-THREAD-', '----------------\nDownload complete!\n----------------')
            os.rename(i, f"files/{i}")
            queue.append(i)

    con.close()

def play_mp3(mp3_filename, window):
    global playing, sound
    window['task'].update(f'Now playing: {mp3_filename}')
    sound = AudioSegment.from_file(f"files/{mp3_filename}", format="mp3")
    playing = playback._play_with_simpleaudio(sound)
    playing.wait_done()
    window['task'].update('No track is currently playing.')
    print("Track finished.")
    #play_obj.stop()
    return


def pause_music(window):
    global playing
    pass


def stop_music(window):
    global playing
    playing.stop()
    window['task'].update("Music stopped.")
    return


def download_mp3(music_name, window):
    query_string = urllib.parse.urlencode({"search_query": music_name})
    formatUrl = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
    search_results = re.findall(r"watch\?v=(\S{11})", formatUrl.read().decode())
    clip = requests.get("https://www.youtube.com/watch?v=" + "{}".format(search_results[0]))
    video_url = "https://www.youtube.com/watch?v=" + "{}".format(search_results[0])

    inspect = BeautifulSoup(clip.content, "html.parser")
    yt_title = inspect.find_all("meta", property="og:title")

    for concatMusic1 in yt_title:
        pass

    print(concatMusic1['content'])

    video_info = youtube_dl.YoutubeDL().extract_info(
        url=video_url, download=False
    )
    filename = f"{video_info['title']}.{video_info['ext']}"
    mp3_filename = f"{video_info['title']}.mp3"
    window['task'].update(f'Now loading: {mp3_filename}')
    if os.path.exists(f"files/{mp3_filename}"):
        window.write_event_value('-THREAD-', 'Found song locally!')
        threading.Thread(target=play_mp3, args=(mp3_filename, window), daemon=True).start()
        return mp3_filename
    options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'logger': ytdlProgress(),
        'progress_hooks': [ytdl_progress_hook],
        'keepvideo': False,
        'outtmpl': filename,
    }

    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download([video_info['webpage_url']])

    if not os.path.exists("files"):
        os.makedirs("files")
    window.write_event_value('-THREAD-', '----------------\nDownload complete!\n----------------')
    os.rename(mp3_filename, f"files/{mp3_filename}")
    threading.Thread(target=play_mp3, args=(mp3_filename, window), daemon=True).start()
    return mp3_filename



def long_operation_thread(seconds, window):
    print('Starting thread - will sleep for {} seconds'.format(seconds))
    time.sleep(seconds)  # sleep for a while
    window.write_event_value('-THREAD-', '** DONE **')  # put a message into queue for GUI

def popup_dropdown(title, text, values):
    popup_window = sg.Window(title,
        [[sg.Text(text)],
        [sg.DropDown(values, key='-DROP-')],
        [sg.OK(bind_return_key=True), sg.Cancel()]
    ])
    popup_event, values = popup_window.read()
    popup_window.close()
    return None if popup_event != 'OK' else values['-DROP-']

def the_gui():
    if config["settings"]["theme"] == "default":
        pass
    else:
        sg.theme(config["settings"]["theme"])

    layout = [[sg.Text('Song name:'), sg.Input(key="music_name")],
              [sg.Text(), sg.Button('Play', bind_return_key=True), sg.Button('Stop'), sg.Button('Add to playlist'),
               sg.Button('Remove from playlist'), sg.Button('Play playlist'), sg.Button('Effects')],
              [sg.Text(size=(40, 1), key='task')],
              [sg.Output(size=(70, 6))]
              ]
    global window
    window = sg.Window('Music Manager', layout)

    # --------------------- EVENT LOOP ---------------------
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        elif event == 'Play':
            window['task'].update(f'Processing...')
            search = (values['music_name'])
            # threading.Thread(target=test, args=(search, window), daemon=True).start()
            threading.Thread(target=download_mp3, args=(search, window,), daemon=True).start()
            # threading.Thread(target=download_mp3, args=(search, window,), daemon=True).start()
        elif event.startswith('Stop'):
            stop_music(window)
        elif event == 'Add to playlist':
            playlist = sg.popup_get_text('Which playlist do you want to add to?', 'Add to playlist')
            if playlist:
                threading.Thread(target=add_to_playlist, args=(values["music_name"], playlist, window),
                                 daemon=True).start()
            else:
                print("No playlist was provided.")
        elif event == 'Remove from playlist':
            playlist = sg.popup_get_text('Which playlist do you want to remove from?', 'Remove from playlist')
            if playlist:
                threading.Thread(target=remove_from_playlist, args=(values["music_name"], playlist, window),
                                 daemon=True).start()
            else:
                print("No playlist was provided.")
        elif event == 'Play playlist':
            playlist = sg.popup_get_text('Which playlist do you want to play?', 'Select playlist')
            if playlist:
                threading.Thread(target=play_playlist, args=(playlist, window),
                                 daemon=True).start()
            else:
                print("No playlist was provided.")
        elif event == 'Effects':
            options = ["Reverse"]
            selected_effect = (popup_dropdown('Effects', 'Choose an effect:', options))
            if selected_effect == 'Reverse':
                global playing, sound
                sound.reverse()
                window['task'].update('Track has been reversed.')
                print("Track has been reversed.")
        elif event == '-THREAD-':
            print(values[event])

    # if user exits the window, then close the window and exit the GUI func
    window.close()


if __name__ == '__main__':
    the_gui()
    print('Exiting Program')
