import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image
import urllib.request
import io
import threading
import ctypes
import yt_dlp
import os
import time
import sys

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ACCENT = "#2563eb"
BG = "#f5f6fa"
CARD = "#ffffff"
BORDER = "#e2e5ea"
MUTED = "#6b7280"

download_history = []

if os.name == "nt":
    myappid = "TubeGrab.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


def get_downloads_folder():
    return os.path.join(os.path.expanduser("~"), "Downloads")



def resource_path(relative_path):
    """Get path to resource, works for dev and for PyInstaller onefile exe"""
    try:
        base_path = sys._MEIPASS  # PyInstaller creates this temp folder at runtime
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ---------------- Helpers ----------------

def format_size(bytes_):
    if not bytes_:
        return "~-- MB"
    mb = bytes_ / (1024 * 1024)
    return f"~{mb:.0f} MB"


def time_ago(ts):
    diff = int(time.time() - ts)
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{diff // 60} min ago"
    if diff < 86400:
        return f"{diff // 3600} hr ago"
    return f"{diff // 86400} day(s) ago"


def format_bytes(b):
    if not b:
        return "0 MB"
    if b >= 1024 ** 3:
        return f"{b / (1024 ** 3):.2f} GB"
    return f"{b / (1024 ** 2):.1f} MB"


def format_eta(seconds):
    if seconds is None:
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


# ---------------- Downloader Logic ----------------

def fetch_info(url, status_label, on_success):
    def worker():
        try:
            status_label.configure(text="Detecting video...")
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(url, download=False)

            thumb_img = None
            thumb_url = info.get("thumbnail")
            if thumb_url:
                try:
                    req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        img_data = resp.read()
                    thumb_img = Image.open(io.BytesIO(img_data))
                except Exception:
                    thumb_img = None

            root.after(0, lambda: on_success(info, thumb_img))
        except Exception as e:
            root.after(0, lambda: status_label.configure(text="Could not detect video"))
            root.after(0, lambda: messagebox.showerror("Error", str(e)))

    threading.Thread(target=worker, daemon=True).start()


class DownloadCancelled(Exception):
    pass


def download_video(url, fmt_string, save_path, status_label, stats_label, progress_bar,
                    download_btn, stop_btn, title, refresh_history, state):
    def hook(d):
        if state.get("cancel"):
            raise DownloadCancelled()

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed')
            eta = d.get('eta')

            percent = (downloaded / total) if total else 0
            speed_txt = f"{format_bytes(speed)}/s" if speed else "-- MB/s"
            eta_txt = format_eta(eta)
            downloaded_txt = format_bytes(downloaded)
            total_txt = format_bytes(total) if total else "?"

            root.after(0, lambda: progress_bar.set(percent))
            root.after(0, lambda: status_label.configure(text=f"Downloading... {int(percent * 100)}%"))
            root.after(0, lambda: stats_label.configure(
                text=f"{downloaded_txt} / {total_txt}   ·   {speed_txt}   ·   ETA {eta_txt}"
            ))
        elif d['status'] == 'finished':
            root.after(0, lambda: status_label.configure(text="Processing..."))
            root.after(0, lambda: stats_label.configure(text="Merging audio & video..."))

    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'format': fmt_string,
        'progress_hooks': [hook],
        'merge_output_format': 'mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        root.after(0, lambda: status_label.configure(text="Download complete!"))
        root.after(0, lambda: stats_label.configure(text=""))
        root.after(0, lambda: progress_bar.set(1))
        download_history.insert(0, {
            "title": title,
            "format": "MP3" if "audio" in fmt_string else "MP4",
            "time": time.time()
        })
        root.after(0, refresh_history)
    except DownloadCancelled:
        root.after(0, lambda: status_label.configure(text="Cancelled"))
        root.after(0, lambda: stats_label.configure(text=""))
        root.after(0, lambda: progress_bar.set(0))
    except Exception as e:
        root.after(0, lambda: status_label.configure(text="Failed"))
        root.after(0, lambda: stats_label.configure(text=""))
        root.after(0, lambda: messagebox.showerror("Download Error", str(e)))
    finally:
        state["cancel"] = False
        root.after(0, lambda: download_btn.configure(state="normal", text="⬇  Download Now"))
        root.after(0, lambda: download_btn.pack(padx=20, pady=(5, 20), anchor="e"))
        root.after(0, lambda: stop_btn.pack_forget())


# ---------------- Downloader UI ----------------

def build_downloader_ui(parent, history_container=None):
    state = {"info": None, "url": None, "cancel": False}
    save_path_var = ctk.StringVar(value=get_downloads_folder())
    quality_var = ctk.StringVar(value="1080")

    outer = ctk.CTkScrollableFrame(parent, fg_color=BG)
    outer.pack(expand=True, fill="both")

    # ---- Hero / search ----
    hero = ctk.CTkFrame(outer, fg_color=BG)
    hero.pack(fill="x", pady=(20, 10))

    ctk.CTkLabel(hero, text="Download YouTube Videos in seconds",
                 font=("Arial", 22, "bold")).pack(pady=(6, 4))
    ctk.CTkLabel(hero, text="Paste any YouTube link and download in your preferred quality.",
                 font=("Arial", 12), text_color=MUTED).pack(pady=(0, 15))

    search_row = ctk.CTkFrame(hero, fg_color="transparent")
    search_row.pack()

    url_entry = ctk.CTkEntry(search_row, width=380, height=42,
                              placeholder_text="Paste YouTube URL here...",
                              corner_radius=10, border_color=BORDER)
    url_entry.pack(side="left", padx=(0, 10))

    detect_status = ctk.CTkLabel(hero, text="", font=("Arial", 11), text_color=MUTED)
    detect_status.pack(pady=(8, 0))

    # ---- Video detected card ----
    card = ctk.CTkFrame(outer, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)

    thumbnail_label = ctk.CTkLabel(card, text="", image=None)
    title_label = ctk.CTkLabel(card, text="", font=("Arial", 14, "bold"), anchor="w", justify="left", wraplength=380)
    meta_label = ctk.CTkLabel(card, text="", font=("Arial", 11), text_color=MUTED, anchor="w")

    radio_frame = ctk.CTkFrame(card, fg_color="transparent")

    progress_bar = ctk.CTkProgressBar(card, width=380)
    progress_bar.set(0)

    status_label = ctk.CTkLabel(card, text="", font=("Arial", 11), text_color=MUTED)
    stats_label = ctk.CTkLabel(card, text="", font=("Arial", 10), text_color=MUTED)
    path_row = ctk.CTkFrame(card, fg_color="transparent")
    path_label = ctk.CTkLabel(path_row, text=save_path_var.get(), font=("Arial", 10), text_color=MUTED)
    
    download_btn = ctk.CTkButton(card, text="⬇  Download Now", width=180, height=36,
                              fg_color=ACCENT, hover_color="#1e4fd1", corner_radius=8)
    choose_folder_btn = ctk.CTkButton(path_row, text="Choose Folder", width=110, height=26,
                                   fg_color="#e5e7eb", text_color="black",
                                   hover_color="#d1d5db")
    stop_btn = ctk.CTkButton(card, text="⏹  Stop", width=100, height=36,
                              fg_color="#dc2626", hover_color="#b91c1c", corner_radius=8)

    def choose_folder():
        folder = filedialog.askdirectory()
        if folder:
            save_path_var.set(folder)
            path_label.configure(text=folder)

    choose_folder_btn.configure(command=choose_folder)

    def refresh_history():
        if history_container is None:
            return
        for w in history_container.winfo_children():
            w.destroy()
        if not download_history:
            ctk.CTkLabel(history_container, text="No downloads yet", font=("Arial", 11), text_color=MUTED).pack(pady=15)
            return
        for item in download_history[:8]:
            row = ctk.CTkFrame(history_container, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f"🎬  {item['title'][:38]}", font=("Arial", 11), anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"{item['format']} · {time_ago(item['time'])}",
                         font=("Arial", 10), text_color=MUTED).pack(side="right")

    def start_download():
        info = state["info"]
        if not info:
            return
        fmt_map = {
            "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "audio": "bestaudio/best",
        }
        fmt_string = fmt_map[quality_var.get()]
        state["cancel"] = False
        progress_bar.set(0)
        download_btn.configure(state="disabled", text="Downloading...")
        status_label.configure(text="Starting...")
        stats_label.configure(text="")

        stop_btn.configure(command=lambda: stop_download())
        stop_btn.pack(padx=20, pady=(5, 20), anchor="e", before=download_btn)

        threading.Thread(
            target=download_video,
            args=(state["url"], fmt_string, save_path_var.get(), status_label, stats_label,
                  progress_bar, download_btn, stop_btn, info.get("title", "video"), refresh_history, state),
            daemon=True
        ).start()

    def stop_download():
        state["cancel"] = True
        status_label.configure(text="Stopping...")

    def show_video_card(info, thumb_img=None):
        state["info"] = info
        title_label.configure(text=info.get("title", "Unknown title"))
        uploader = info.get("uploader", "Unknown channel")
        views = info.get("view_count")
        views_txt = f"{views:,} views" if views else ""
        meta_label.configure(text=f"{uploader}  ·  {views_txt}")

        if thumb_img:
            w, h = thumb_img.size
            target_w = 380
            target_h = int(h * (target_w / w))
            ctk_img = ctk.CTkImage(light_image=thumb_img, dark_image=thumb_img,
                                    size=(target_w, target_h))
            thumbnail_label.configure(image=ctk_img, text="")
            thumbnail_label.image = ctk_img
        else:
            thumbnail_label.configure(image=None, text="No thumbnail")

        for w in radio_frame.winfo_children():
            w.destroy()

        filesize = info.get("filesize") or info.get("filesize_approx")
        options = [
            ("1080", "MP4 — 1080p HD", format_size(filesize), "Best Quality"),
            ("720", "MP4 — 720p", format_size(filesize * 0.55 if filesize else None), ""),
            ("480", "MP4 — 480p", format_size(filesize * 0.25 if filesize else None), ""),
            ("audio", "MP3 — Audio only", format_size(filesize * 0.08 if filesize else None), "Audio"),
        ]
        for val, label, size, tag in options:
            row = ctk.CTkFrame(radio_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkRadioButton(row, text=label, variable=quality_var, value=val,
                                fg_color=ACCENT).pack(side="left")
            if tag:
                ctk.CTkLabel(row, text=tag, font=("Arial", 9, "bold"), text_color=ACCENT,
                             fg_color="#dbeafe", corner_radius=6, padx=6).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=size, font=("Arial", 10), text_color=MUTED).pack(side="right")

        detect_status.configure(text="")
        card.pack(fill="x", padx=40, pady=20)
        thumbnail_label.pack(padx=20, pady=(20, 10))
        title_label.pack(fill="x", padx=20, pady=(0, 2), anchor="w")
        meta_label.pack(fill="x", padx=20, pady=(0, 15), anchor="w")
        radio_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        path_row.pack(fill="x", padx=20, pady=(5, 5))
        path_label.pack(side="left")
        choose_folder_btn.pack(side="right")

        progress_bar.pack(fill="x", padx=20, pady=10)
        status_label.pack(padx=20, anchor="w")
        stats_label.pack(padx=20, anchor="w", pady=(0, 5))
        download_btn.configure(command=start_download)
        download_btn.pack(padx=20, pady=(5, 20), anchor="e")

    def on_detect():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please paste a YouTube URL first.")
            return
        state["url"] = url
        fetch_info(url, detect_status, show_video_card)

    detect_btn = ctk.CTkButton(search_row, text="Download", width=100, height=42,
                                fg_color=ACCENT, hover_color="#1e4fd1", corner_radius=10,
                                command=on_detect)
    detect_btn.pack(side="left")

    refresh_history()
    return refresh_history


# ---------------- Dashboard ----------------

def top_bar(parent):
    bar = ctk.CTkFrame(parent, fg_color=CARD, height=50, corner_radius=0)
    bar.pack(fill="x")
    ctk.CTkLabel(bar, text="▶  TubeGrab", font=("Arial", 14, "bold"), text_color=ACCENT).pack(side="left", padx=15, pady=10)


def main():
    """Downloader dashboard"""
    root.configure(fg_color=BG)
    top_bar(root)

    body = ctk.CTkFrame(root, fg_color=BG)
    body.pack(expand=True, fill="both")

    history_card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
    history_container = ctk.CTkFrame(history_card, fg_color="transparent")

    build_downloader_ui(body, history_container)

    ctk.CTkLabel(history_card, text="RECENT DOWNLOADS", font=("Arial", 11, "bold"),
                 text_color=MUTED, anchor="w").pack(fill="x", padx=20, pady=(15, 5))
    history_container.pack(fill="x", padx=20, pady=(0, 15))
    history_card.pack(fill="x", padx=40, pady=(0, 30))


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("TubeGrab")
    root.geometry("620x750")
    root.resizable(False, False)

    ico_path = resource_path("icon.ico")
    png_path = resource_path("icon.png")

    print("Looking for icon at:", ico_path)
    print("File exists?", os.path.exists(png_path))
    
    try:
        root.iconbitmap(ico_path)
        print("ICO icon set")
    except Exception as e:
        print("ICO failed:", e)
        try:
            icon_img = tk.PhotoImage(file=png_path)
            root.after(200, lambda: root.iconphoto(True, icon_img))
            print("PNG icon set as fallback")
        except Exception as e2:
            print("PNG fallback also failed:", e2)

    main()

    root.mainloop()