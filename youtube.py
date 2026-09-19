import yt_dlp

url = "https://www.youtube.com/watch?v=pKvXczbkr2s"

options = {
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "merge_output_format": "mp4",
    "ffmpeg_location": r"C:\Users\muham\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe",
    "cookiesfrombrowser": ("firefox",),
}

with yt_dlp.YoutubeDL(options) as ydl:
    ydl.download([url])