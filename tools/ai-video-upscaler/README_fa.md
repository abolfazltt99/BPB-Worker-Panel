# ابزار ویندوزی ارتقای AI ویدیو

این ابزار یک برنامهٔ گرافیکی مستقل است و **واقعاً هر فریم را با مدل Real-ESRGAN پردازش می‌کند**؛ CSS، شارپ‌سازی ساده یا بزرگ‌کردن ظاهری نیست. برای فیلم و سریال 720p، ابتدا مدل AI تصویر را دو برابر می‌کند و سپس در حالت 1080p با فیلتر Lanczos به ابعاد 1920×1080 می‌رسد. حالت 2K همان خروجی دوبرابری 2560×1440 است.

> کارت GT 630 با 2GB VRAM برای این کار بسیار کند است. تنظیم پیش‌فرض `tile=128` و یک job انتخاب شده تا احتمال خطای کمبود VRAM پایین بماند. اگر خطای حافظه/Vulkan دیدید tile را به 96 یا 64 کاهش دهید. انتظار زمان چندین ساعت برای هر فیلم بلند طبیعی است.

## ساخت برنامهٔ EXE (پیشنهادی)

این مخزن فایل باینری چندصد مگابایتی را commit نمی‌کند، اما اسکریپت آماده دارد که یک **فایل واحد و قابل‌انتقال `AI-Video-Upscaler.exe`** می‌سازد. در ویندوز PowerShell را در همین پوشه باز کنید و اجرا کنید:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1 -DownloadRuntime
```

اسکریپت، FFmpeg، Real-ESRGAN NCNN Vulkan، مدل‌ها و PyInstaller را دریافت می‌کند و سپس برنامه را در مسیر زیر می‌سازد:

```text
tools\ai-video-upscaler\dist\AI-Video-Upscaler.exe
```

این EXE هنگام شروع runtimeها و مدل را موقتاً extract می‌کند؛ بنابراین اجرای نخست و حجم فایل زیادتر است، اما برای استفادهٔ نهایی **نصب Python، FFmpeg یا Real-ESRGAN لازم نیست**. برای اجرا فقط روی `AI-Video-Upscaler.exe` دوبار کلیک کنید.

همچنین workflow گیت‌هاب در هر push به شاخهٔ اصلی یا اجرای دستی، artifact آمادهٔ `AI-Video-Upscaler-windows` را تولید می‌کند؛ فایل workflow در `.github/workflows/ai-video-upscaler-windows.yml` است.

## اجرای نسخهٔ Python (برای توسعه)

1. [Python 3 برای ویندوز](https://www.python.org/downloads/windows/) را نصب کنید و گزینهٔ **Add Python to PATH** را فعال کنید.
2. نسخهٔ Windows پروژهٔ [Real-ESRGAN NCNN Vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases) را دانلود و از حالت zip خارج کنید.
3. از نسخهٔ استخراج‌شده، `realesrgan-ncnn-vulkan.exe` و پوشهٔ `models` را به این ساختار منتقل کنید:

   ```text
   ai-video-upscaler/
   ├─ bin/
   │  ├─ realesrgan-ncnn-vulkan.exe
   │  ├─ models/
   │  │  └─ realesrgan-x4plus.*
   │  ├─ ffmpeg.exe
   │  └─ ffprobe.exe
   ├─ run_upscaler.bat
   └─ video_upscaler.py
   ```

4. یک Windows build شامل `ffmpeg.exe` و `ffprobe.exe` از [FFmpeg](https://ffmpeg.org/download.html) دانلود کنید و هر دو فایل را در همان `bin` قرار دهید.
5. `run_upscaler.bat` را اجرا کنید، ویدیوی ورودی و محل خروجی با پسوند **`.mkv`** را انتخاب کنید، سپس `1080p` یا `1440p (2K)` را انتخاب کنید.

## کیفیت و محدودیت‌ها

- مدل پیش‌فرض `realesrgan-x4plus` برای ویدیوی واقعی مناسب است؛ برای انیمه بهتر است نام مدل را در `video_upscaler.py` به `realesr-animevideov3` تغییر دهید (به شرط وجود مدل در پوشهٔ `models`).
- خروجی 1080p با CRF 16 و preset `slow` encode می‌شود تا فشرده‌سازی کیفیت AI را بی‌دلیل خراب نکند. حجم خروجی ممکن است بسیار زیاد شود.
- فایل صوتی، زیرنویس و metadata از فایل اصلی کپی می‌شوند؛ خروجی MKV را نگه دارید تا احتمال ناسازگاری زیرنویس کمتر باشد.
- ویدیوهای DRMدار سرویس‌های استریم ورودی مناسب این ابزار نیستند؛ ابزار فقط روی فایل ویدیویی محلی کار می‌کند.
- ارتقای AI می‌تواند جزئیات ادراک‌شده را بهتر کند، اما جزئیات دقیقِ ثبت‌نشده در نسخهٔ 720p را تضمین نمی‌کند و در صحنه‌های بسیار تار/نویزی ممکن است artefact بسازد. قبل از پردازش کامل، ابتدا یک کلیپ کوتاه را آزمایش کنید.
