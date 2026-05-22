# claude-skill-bilibili-downloader

Download Bilibili videos to local MP4. Pure Python, no GUI, no yt-dlp.

## Install

```bash
cp -r . ~/.claude/skills/bilibili-downloader/
```

## Requirements

- Python 3.9+
- `pip install httpx`
- `ffmpeg` (e.g. `brew install ffmpeg`)

## Use

```bash
python scripts/download_bilibili.py "https://www.bilibili.com/video/BVxxxxxxxxxx"
python scripts/download_bilibili.py BVxxxxxxxxxx --output-dir ~/Movies
```

Default output: `~/Downloads/bilibili_videos/`

## What it does

1. Fetches WBI keys from Bilibili API
2. Gets video metadata & stream URLs
3. Downloads DASH video + audio separately
4. Merges with ffmpeg into MP4
5. Cleans up temp files

## Limitations

- Max 480P without login (Bilibili restriction)
- No subtitles or danmaku

## License

MIT
