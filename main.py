import customtkinter as ctk
import os
import tkinter as tk
import threading
import queue
import subprocess
import ctypes
import re
import youtube_dl

from customtkinter import *
from ctypes import windll, byref, sizeof, c_int
from tkinter import Menu, ttk, END
from tkinter.filedialog import askdirectory
from pytube import *

# Create a queue object
q = queue.Queue()
# ctk.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"
bg_color = "#111111"
fg_color = "#a91b0d"
text_color = "white"
hover_color = "#800000"
customfont = ("Roboto", 12)

desktop_path = os.environ["USERPROFILE"] + "\Desktop"
save_path = ""
progress_bar = ""
progress_label = ""
filename = ""
url = ""
website = "youtube"


def website_radio_toggle(radio_var):
    if radio_var == "youtube":
        title_preview_label.place(x=430, y=120)
        load_url_button.place(x=320, y=20)
        download_url_button.place_forget()
        root.geometry("700x480")

    elif radio_var == "other":
        title_preview_label.place_forget()
        load_url_button.place_forget()
        download_url_button.place(x=320, y=20)
        root.geometry("700x145")

    elif radio_var == "mp3":
        title_preview_label.place_forget()
        load_url_button.place_forget()
        download_url_button.place(x=320, y=20)
        root.geometry("700x145")


def merge_audio_video(video_file: str, audio_file: str, output_file: str):
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_file,
        "-i",
        audio_file,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-strict",
        "experimental",
        output_file,
    ]

    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        os.remove(video_file)
        os.remove(audio_file)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {str(e)}")
        print(f"Command output: {e.output.decode()}")
    except OSError as e:
        print(f"Error: {e.filename} - {e.strerror}.")


def load_url(url_entry, videos_listbox, title_label, thumbnail):
    global url
    try:
        url = url_entry.get()

        try:
            videos_listbox.delete(0, END)
        except:
            print("")

        youtube_object = YouTube(url)
        stream_object = youtube_object.streams.filter(
            adaptive=True, file_extension="webm"
        )

        title_label.configure(text=youtube_object.title)

        idx = 0

        for stream in stream_object:
            
            videos_listbox.insert(
                idx, stream.resolution + " - " + str(stream.fps) + " fps"
            )
            idx += 1
            print(stream)

        thumbnail_object = tk.PhotoImage(file=youtube_object.thumbnail_url)
        thumbnail_object = ctk.CTkImage(file=youtube_object.thumbnail_url)
        thumbnail.configure(image=thumbnail_object)

    except Exception as e:
        print("error - ", e)


def on_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = bytes_downloaded / total_size * 100
    per = str(int(percentage))
    q.put(per)



def download(videos_listbox, save_path_entry, filename_entry=""):
    global url

    filename = filename_entry.get()
    save_path = save_path_entry.get()
    selected_index = videos_listbox.curselection()

    if selected_index:
        selected_index = selected_index[0]
        youtube_object = YouTube(url, on_progress_callback=on_progress)
        stream_object = youtube_object.streams.filter(
            adaptive=True, progressive=False, file_extension="mp4"
        )
        selected_stream = stream_object[selected_index]
        audio_stream = youtube_object.streams.get_audio_only()

        if filename == "":
            filename = youtube_object.title
        else:
            filename = "OnlineVideo"
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)

        # Create a thread for the download task
        download_video_thread = threading.Thread(
            target=selected_stream.download,
            args=(save_path, "video_" + filename + ".mp4"),
        )
        download_thread_audio = threading.Thread(
            target=audio_stream.download, args=(save_path, "audio_" + filename + ".mp4")
        )

        # Start the thread
        download_video_thread.start()
        download_thread_audio.start()

        # Update the progress bar and label in the main thread
        while download_video_thread.is_alive():
            root.update()  # update the GUI
            try:
                # Try to get the progress from the queue and update the GUI
                progress = q.get_nowait()
                progress_label.configure(text=progress + " %")
                progress_bar.set(float(progress) / 100)
            except queue.Empty:
                pass
        download_video_thread.join()
        download_thread_audio.join()

        merge_audio_video(
            save_path + "/video_" + filename + ".mp4",
            save_path + "/audio_" + filename + ".mp4",
            save_path + "/" + filename + ".mp4",
        )


def download_alternate(website_radio_var, url, save_path):
    global progress_other_bar, progress_other_label
    outtmpl = save_path + "/%(title)s.%(ext)s"

    if website_radio_var == "other":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": outtmpl,
        }

    elif website_radio_var == "mp3":
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
                    "outtmpl": outtmpl,
        }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def browse_directory(save_path_entry):
    location = askdirectory()
    save_path_entry.delete(0, END)
    save_path_entry.insert(END, location)


def menu_bar_setup(root):
    customfont = ("Roboto", 11)
    menubar = Menu(root)

    file_menu = Menu(menubar, tearoff=0, relief="flat", bd=0, activeborderwidth=0)
    file_menu.config(bg="gray20", fg="white", font=customfont)

    menubar.add_cascade(label="File", menu=file_menu)

    file_menu.add_command(
        label="Exit",
        command=lambda: root.destroy(),
        activebackground=hover_color,
        foreground=text_color,
        background=fg_color,
    )

    root.config(menu=menubar)


def root_widgets(root):
    global save_path, progress_bar, progress_label, filename, website
    global title_preview_label, download_url_button, load_url_button
    global progress_other_label, progress_other_bar

    website_radio_var = ctk.StringVar(root)
    url = ctk.StringVar(root)
    save_path = ctk.StringVar(root)

    # ----------------------------------------------# LABELS #----------------------------------------------#
    load_url_label = ctk.CTkLabel(
        root,
        font=customfont,
        text="URL:",
        width=80,
        height=20,
        bg_color=bg_color,
        text_color=fg_color,
    )
    load_url_label.place(x=20, y=20)

    browse_directory_label = ctk.CTkLabel(
        root,
        font=customfont,
        text="Directory:",
        width=80,
        height=20,
        bg_color=bg_color,
        text_color=fg_color,
    )
    browse_directory_label.place(x=20, y=50)

    save_as_label = ctk.CTkLabel(
        root,
        font=customfont,
        text="Save as:",
        width=80,
        height=20,
        bg_color=bg_color,
        text_color=fg_color,
    )
    save_as_label.place(x=20, y=80)

    title_preview_label = ctk.CTkLabel(
        root,
        width=250,
        height=20,
        text="Title Preview",
        bg_color=bg_color,
        text_color=fg_color,
    )
    title_preview_label.place(x=430, y=120)

    available_streams_label = ctk.CTkLabel(
        root,
        width=360,
        height=20,
        text="Available Streams",
        bg_color=bg_color,
        text_color=fg_color,
    )
    available_streams_label.place(x=20, y=140)

    # ----------------------------------------------# Inputs #----------------------------------------------#
    load_url_entry = ctk.CTkEntry(
        root,
        font=customfont,
        textvariable=url,
        placeholder_text="Paste your URL here",
        width=200,
        height=20,
        bg_color=bg_color,
        text_color=fg_color,
        placeholder_text_color=fg_color,
        fg_color="black",
    )
    load_url_entry.place(x=110, y=20)

    save_path_entry = ctk.CTkEntry(
        root,
        textvariable=save_path,
        font=customfont,
        width=200,
        height=20,
        bg_color=bg_color,
        text_color=fg_color,
        fg_color="black",
    )
    save_path_entry.insert(0, desktop_path)
    save_path_entry.place(x=110, y=50)

    filename_entry = ctk.CTkEntry(
        root,
        textvariable=filename,
        font=customfont,
        placeholder_text="Name of the file",
        width=200,
        height=20,
        bg_color=bg_color,
        text_color=fg_color,
        placeholder_text_color=fg_color,
        fg_color="black",
    )
    filename_entry.place(x=110, y=80)

    # ----------------------------------------------# BUTTONS #----------------------------------------------#
    load_url_button = ctk.CTkButton(
        root,
        font=customfont,
        text="Load Url",
        width=70,
        height=20,
        command=lambda: load_url(
            load_url_entry, videos_listbox, title_preview_label, thumbnail
        ),
        bg_color=bg_color,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
    )
    load_url_button.place(x=320, y=20)

    download_url_button = ctk.CTkButton(
        root,
        font=customfont,
        text="Download",
        width=70,
        height=20,
        command=lambda: download_alternate(
            website_radio_var.get(), url.get(), save_path.get()
        ),
        bg_color=bg_color,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
    )
    download_url_button.place(x=320, y=20)
    download_url_button.place_forget()

    browse_directory_button = ctk.CTkButton(
        root,
        font=customfont,
        text="Browse",
        width=70,
        height=20,
        command=lambda: browse_directory(save_path_entry),
        bg_color=bg_color,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
    )
    browse_directory_button.place(x=320, y=50)

    download_button = ctk.CTkButton(
        root,
        font=customfont,
        text="Download selected",
        width=240,
        height=20,
        command=lambda: download(videos_listbox, save_path_entry, filename_entry),
        bg_color=bg_color,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
    )
    download_button.place(x=430, y=385)

    # ----------------------------------------------# Radio Buttons #----------------------------------------------#
    website1 = ctk.CTkRadioButton(
        root,
        text="Youtube",
        variable=website_radio_var,
        value="youtube",
        font=customfont,
        fg_color="red",
        bg_color=bg_color,
        text_color=fg_color,
        command=lambda: website_radio_toggle(website_radio_var.get()),
    )
    website1.place(x=430, y=20)
    website2 = ctk.CTkRadioButton(
        root,
        text="Other Websites",
        variable=website_radio_var,
        value="other",
        font=customfont,
        fg_color="red",
        bg_color=bg_color,
        text_color=fg_color,
        command=lambda: website_radio_toggle(website_radio_var.get()),
    )
    website2.place(x=430, y=50)
    website3 = ctk.CTkRadioButton(
        root,
        text="MP3",
        variable=website_radio_var,
        value="mp3",
        font=customfont,
        fg_color="red",
        bg_color=bg_color,
        text_color=fg_color,
        command=lambda: website_radio_toggle(website_radio_var.get()),
    )
    website3.place(x=430, y=80)

    website1.select()
    # ----------------------------------------------# THUMBNAIL #----------------------------------------------#
    thumbnail = ctk.CTkLabel(
        root,
        width=250,
        height=135,
        text="Thumbnail Preview",
        image=None,
        bg_color=bg_color,
        text_color=fg_color,
    )
    thumbnail.place(x=430, y=150)

    # ----------------------------------------------# LISTBOX #----------------------------------------------#
    videos_listbox = tk.Listbox(
        root,
        width=49,
        height=17,
        bg=bg_color,
        foreground="white",
        font=customfont,
        selectmode=tk.SINGLE,
    )
    videos_listbox.place(x=25, y=205)

    # ----------------------------------------------# Image #----------------------------------------------#
    icon_image = tk.PhotoImage(
        file=(os.path.dirname(os.path.abspath(__file__)) + "/Assets/play.png")
    )
    icon = ctk.CTkLabel(
        root,
        text="",
        width=40,
        height=40,
        bg_color=bg_color,
        text_color=fg_color,
        image=icon_image,
    )
    icon.place(x=375, y=90)

    # ----------------------------------------------# PROGRESS BAR #----------------------------------------------#
    progress_bar = ctk.CTkProgressBar(
        root, width=250, height=10, fg_color="#333333", progress_color=fg_color
    )
    progress_bar.set(0.0)
    progress_bar.place(x=430, y=430)

    progress_label = ctk.CTkLabel(
        root,
        text="% - 0",
        font=customfont,
        width=20,
        height=10,
        text_color=text_color,
        bg_color=bg_color,
        fg_color=bg_color,
    )
    progress_label.place(x=430, y=410)

    # ----------------------------------------------# SEPARATORS #----------------------------------------------#
    ctk.CTkLabel(
        root,
        # bg_color="#1f538d",
        bg_color=fg_color,
        text="",
        width=2,
        height=63,
    ).place(x=400, y=20)
    ctk.CTkLabel(
        root,
        # bg_color="#1f538d",
        bg_color=fg_color,
        text="",
        width=2,
        height=290,
    ).place(x=400, y=150)


# ----------------------------------------------# MAIN LOOP #----------------------------------------------#
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Online Videos Downloader")
    root.config(bg="#111111")
    root.iconbitmap(os.path.dirname(os.path.abspath(__file__)) + "/Assets/icon.ico")
    root.geometry("700x480")
    root.resizable(False, False)
    root.eval("tk::PlaceWindow . Center")
    root.protocol("WM_DELETE_WINDOW", lambda: root.destroy())

    root_widgets(root)
    menu_bar_setup(root)

    root.mainloop()
