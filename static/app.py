import os, re, uuid, subprocess, shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort

app = Flask(__name__)
BASE = Path("/tmp/slicefree")
BASE.mkdir(exist_ok=True)
MAX_CLIP_SECONDS = int(os.getenv("MAX_CLIP_SECONDS", "3600"))

def valid_youtube_url(url):
    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url.strip()))

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/info")
def info():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    if not valid_youtube_url(url):
        return jsonify(error="Enter a valid YouTube URL."), 400
    # Metadata only. Download/export is intended for videos the user owns or is authorized to use.
    cmd = ["yt-dlp", "--no-warnings", "--dump-single-json", "--skip-download", url]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if p.returncode:
            return jsonify(error="Could not read this video. It may be private, restricted, or unavailable."), 400
        import json
        meta = json.loads(p.stdout)
        return jsonify(title=meta.get("title","YouTube video"),
                       duration=meta.get("duration") or 0,
                       thumbnail=meta.get("thumbnail",""))
    except subprocess.TimeoutExpired:
        return jsonify(error="Video lookup timed out. Try again."), 408

@app.post("/api/clip")
def clip():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    start, end = data.get("start"), data.get("end")
    quality = str(data.get("quality", "best"))
    fmt = data.get("format", "mp4")
    authorized = data.get("authorized") is True
    if not authorized:
        return jsonify(error="Please confirm you own this video or have permission to use it."), 400
    if not valid_youtube_url(url):
        return jsonify(error="Enter a valid YouTube URL."), 400
    try:
        start, end = float(start), float(end)
    except (TypeError, ValueError):
        return jsonify(error="Enter valid start and end times."), 400
    duration = end - start
    if start < 0 or duration <= 0 or duration > MAX_CLIP_SECONDS:
        return jsonify(error=f"Clip must be between 1 second and {MAX_CLIP_SECONDS // 60} minutes."), 400
    if fmt not in ("mp4", "mp3", "m4a", "mov"):
        return jsonify(error="Unsupported format."), 400
    job = uuid.uuid4().hex
    work = BASE / job
    work.mkdir()
    out = work / "clip.%(ext)s"
    # Select best available source up to requested ceiling; 'best' means highest available.
    formats = {
        "best": "bv*+ba/b",
        "2160": "bv*[height<=2160]+ba/b[height<=2160]",
        "1440": "bv*[height<=1440]+ba/b[height<=1440]",
        "1080": "bv*[height<=1080]+ba/b[height<=1080]",
        "720": "bv*[height<=720]+ba/b[height<=720]",
        "480": "bv*[height<=480]+ba/b[height<=480]",
    }
    if quality not in formats:
        shutil.rmtree(work, ignore_errors=True)
        return jsonify(error="Invalid quality selection."), 400
    section = f"*{start:.3f}-{end:.3f}"
    cmd = ["yt-dlp", "--no-warnings", "--no-playlist", "--download-sections", section,
           "--force-keyframes-at-cuts", "-f", formats[quality], "--merge-output-format", "mp4",
           "-o", str(out), url]
    if fmt in ("mp3", "m4a"):
        cmd += ["-x", "--audio-format", fmt]
    elif fmt == "mov":
        cmd += ["--recode-video", "mov"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if p.returncode:
            shutil.rmtree(work, ignore_errors=True)
            return jsonify(error="Clip export failed. The video may be restricted, unavailable, or unsupported."), 400
        candidates = [x for x in work.iterdir() if x.is_file()]
        if not candidates:
            raise RuntimeError("No output file created")
        file = candidates[0]
        response = send_file(file, as_attachment=True, download_name=f"slicefree-clip.{fmt}")
        response.call_on_close(lambda: shutil.rmtree(work, ignore_errors=True))
        return response
    except subprocess.TimeoutExpired:
        shutil.rmtree(work, ignore_errors=True)
        return jsonify(error="Export timed out. Try a shorter clip or lower resolution."), 408
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        return jsonify(error="Something went wrong while creating the clip."), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
