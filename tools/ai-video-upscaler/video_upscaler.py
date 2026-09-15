"""Windows GUI for AI video upscaling with Real-ESRGAN NCNN Vulkan.

This app deliberately runs the AI model outside the browser/Cloudflare Worker:
video frames must be processed on the user's PC.  It is designed to remain
usable on low-VRAM cards by using a small tile size and one Vulkan job.
"""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, BooleanVar, IntVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk


# PyInstaller extracts a one-file build to ``_MEIPASS``.  Keeping the runtime
# beside that extraction directory makes the same code work in development,
# in the portable folder build, and in the final one-file EXE.
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
BIN_DIR = APP_DIR / "bin"
FFMPEG = BIN_DIR / "ffmpeg.exe"
FFPROBE = BIN_DIR / "ffprobe.exe"
REALESRGAN = BIN_DIR / "realesrgan-ncnn-vulkan.exe"


@dataclass(frozen=True)
class Preset:
    label: str
    output_height: int


PRESETS = (Preset("1080p (Full HD)", 1080), Preset("1440p (2K)", 1440))


class UpscaleError(RuntimeError):
    """An expected failure that can be shown to the user."""


class VideoUpscaler:
    def __init__(self, log: queue.Queue[str], cancel: threading.Event) -> None:
        self.log = log
        self.cancel = cancel

    def write(self, text: str) -> None:
        self.log.put(text)

    def run_command(self, args: list[str], title: str) -> None:
        self.write(f"\n--- {title} ---")
        self.write("$ " + subprocess.list2cmdline(args))
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace")
        assert process.stdout is not None
        for line in process.stdout:
            if self.cancel.is_set():
                process.terminate()
                process.wait(timeout=10)
                raise UpscaleError("عملیات توسط کاربر متوقف شد.")
            line = line.strip()
            if line:
                self.write(line)
        if process.wait() != 0:
            raise UpscaleError(f"{title} با خطا تمام شد (کد {process.returncode}).")

    def probe(self, source: Path) -> tuple[int, int, str]:
        result = subprocess.run(
            [str(FFPROBE), "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate", "-of", "json", str(source)],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        stream = json.loads(result.stdout)["streams"][0]
        return int(stream["width"]), int(stream["height"]), stream["r_frame_rate"]

    def upscale(self, source: Path, destination: Path, preset: Preset, tile: int,
                keep_frames: bool) -> None:
        missing = [path.name for path in (FFMPEG, FFPROBE, REALESRGAN) if not path.is_file()]
        if missing:
            raise UpscaleError("فایل‌های لازم پیدا نشدند: " + "، ".join(missing))

        width, height, frame_rate = self.probe(source)
        if height > preset.output_height:
            raise UpscaleError("ارتفاع ویدیوی ورودی از خروجی انتخاب‌شده بیشتر است؛ upscale لازم نیست.")
        self.write(f"ویدیوی ورودی: {width}×{height} با نرخ {frame_rate} fps")
        self.write("مدل AI: Real-ESRGAN x4plus؛ پردازش با Vulkan و tile کوچک برای VRAM پایین.")

        work = destination.parent / f".{destination.stem}_ai_work"
        raw = work / "raw"
        enhanced = work / "enhanced"
        shutil.rmtree(work, ignore_errors=True)
        raw.mkdir(parents=True)
        enhanced.mkdir()
        try:
            self.run_command([str(FFMPEG), "-hide_banner", "-y", "-i", str(source), "-map", "0:v:0",
                              "-vsync", "0", "-compression_level", "3", str(raw / "frame_%08d.png")],
                             "استخراج فریم‌ها")
            self.run_command([str(REALESRGAN), "-i", str(raw), "-o", str(enhanced), "-n",
                              "realesrgan-x4plus", "-s", "2", "-t", str(tile), "-j", "1:1:1", "-f", "png"],
                             "بهبود AI با Real-ESRGAN")

            # Generate 2x AI frames first.  720p -> 1080p is then a high-quality downscale;
            # 720p -> 1440p keeps the native 2x AI result.
            video_filter = (
                f"scale=-2:{preset.output_height}:flags=lanczos,"
                "format=yuv420p"
            )
            self.run_command([str(FFMPEG), "-hide_banner", "-y", "-framerate", frame_rate,
                              "-i", str(enhanced / "frame_%08d.png"), "-i", str(source),
                              "-map", "0:v:0", "-map", "1:a?", "-map", "1:s?", "-map_metadata", "1",
                              "-vf", video_filter, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                              "-c:a", "copy", "-c:s", "copy", str(destination)], "ساخت فایل نهایی")
            self.write(f"\nتمام شد: {destination}")
        finally:
            if not keep_frames:
                shutil.rmtree(work, ignore_errors=True)
            else:
                self.write(f"فریم‌های کاری نگه داشته شدند: {work}")


class App:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("AI Video Upscaler — Real-ESRGAN")
        root.minsize(720, 520)
        self.source = StringVar()
        self.destination = StringVar()
        self.preset = StringVar(value=PRESETS[0].label)
        self.tile = IntVar(value=128)
        self.keep_frames = BooleanVar(value=False)
        self.log: queue.Queue[str] = queue.Queue()
        self.cancel = threading.Event()
        self.running = False
        self._build()
        root.after(100, self._drain_log)

    def _build(self) -> None:
        content = ttk.Frame(self.root, padding=14)
        content.pack(fill=BOTH, expand=True)
        ttk.Label(content, text="AI Video Upscaler", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(content, text="Real-ESRGAN برای ارتقای واقعی فریم‌ها؛ مناسب 720p → 1080p یا 2K").pack(anchor="w", pady=(0, 12))
        self._file_row(content, "ویدیوی ورودی", self.source, self.pick_source)
        self._file_row(content, "فایل خروجی", self.destination, self.pick_destination)
        settings = ttk.Frame(content)
        settings.pack(fill=X, pady=8)
        ttk.Label(settings, text="رزولوشن خروجی:").pack(side=LEFT)
        ttk.Combobox(settings, textvariable=self.preset, values=[p.label for p in PRESETS], state="readonly", width=20).pack(side=LEFT, padx=(8, 20))
        ttk.Label(settings, text="Tile (برای GT 630: 128):").pack(side=LEFT)
        ttk.Spinbox(settings, from_=64, to=512, increment=32, textvariable=self.tile, width=6).pack(side=LEFT, padx=8)
        ttk.Checkbutton(content, text="فریم‌های موقت PNG را نگه دار (فضای دیسک بسیار زیادی می‌خواهد)", variable=self.keep_frames).pack(anchor="w")
        controls = ttk.Frame(content)
        controls.pack(fill=X, pady=10)
        self.start_button = ttk.Button(controls, text="شروع پردازش AI", command=self.start)
        self.start_button.pack(side=LEFT)
        self.stop_button = ttk.Button(controls, text="توقف", command=self.stop, state="disabled")
        self.stop_button.pack(side=LEFT, padx=8)
        self.progress = ttk.Progressbar(controls, mode="indeterminate")
        self.progress.pack(side=RIGHT, fill=X, expand=True)
        self.output = ttk.Treeview(content, columns=("log",), show="headings", height=15)
        self.output.heading("log", text="گزارش پردازش")
        self.output.column("log", width=680, stretch=True)
        self.output.pack(fill=BOTH, expand=True)

    def _file_row(self, parent: ttk.Frame, label: str, variable: StringVar, command) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=4)
        ttk.Label(row, text=label, width=14).pack(side=LEFT)
        ttk.Entry(row, textvariable=variable).pack(side=LEFT, fill=X, expand=True, padx=8)
        ttk.Button(row, text="انتخاب…", command=command).pack(side=RIGHT)

    def pick_source(self) -> None:
        filename = filedialog.askopenfilename(filetypes=[("Video files", "*.mkv *.mp4 *.avi *.mov *.webm"), ("All files", "*.*")])
        if filename:
            self.source.set(filename)
            path = Path(filename)
            self.destination.set(str(path.with_name(path.stem + "_AI_1080p.mkv")))

    def pick_destination(self) -> None:
        filename = filedialog.asksaveasfilename(defaultextension=".mkv", filetypes=[("Matroska video", "*.mkv")])
        if filename:
            self.destination.set(filename)

    def start(self) -> None:
        source, destination = Path(self.source.get()), Path(self.destination.get())
        if not source.is_file() or not self.destination.get():
            messagebox.showerror("ورودی نامعتبر", "یک فایل ورودی و مسیر خروجی انتخاب کنید.")
            return
        if source.resolve() == destination.resolve():
            messagebox.showerror("مسیر نامعتبر", "مسیر خروجی باید با فایل ورودی متفاوت باشد.")
            return
        preset = next(item for item in PRESETS if item.label == self.preset.get())
        self.running, self.cancel = True, threading.Event()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress.start(12)
        self.log.put("شروع شد. این فرآیند برای فیلم بلند ممکن است ساعت‌ها طول بکشد.")
        threading.Thread(target=self._worker, args=(source, destination, preset), daemon=True).start()

    def _worker(self, source: Path, destination: Path, preset: Preset) -> None:
        try:
            VideoUpscaler(self.log, self.cancel).upscale(source, destination, preset, self.tile.get(), self.keep_frames.get())
        except (UpscaleError, subprocess.CalledProcessError, OSError, KeyError, json.JSONDecodeError) as error:
            self.log.put(f"\nخطا: {error}")
        finally:
            self.log.put("__FINISHED__")

    def stop(self) -> None:
        self.cancel.set()
        self.stop_button.configure(state="disabled")
        self.log.put("درخواست توقف ثبت شد…")

    def _drain_log(self) -> None:
        try:
            while True:
                message = self.log.get_nowait()
                if message == "__FINISHED__":
                    self.running = False
                    self.progress.stop()
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    continue
                self.output.insert("", END, values=(message,))
                self.output.yview_moveto(1)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)


if __name__ == "__main__":
    window = Tk()
    App(window)
    window.mainloop()
