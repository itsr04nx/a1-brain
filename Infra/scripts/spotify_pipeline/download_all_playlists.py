import os
import sys
import re
import json
import time
import shutil
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TPOS, APIC, USLT, ID3NoHeaderError

CATALOG_PATH = r"C:\Users\Wissen\Downloads\Spotify\master_catalog.json"
LOCAL_DIR = r"C:\Users\Wissen\Downloads\Spotify\all_music"
REMOTE_DEST = "micro-2:/home/ubuntu/koel/music/Tracks/"
KOEL_URL = "https://koel.rohan.run.place"

os.makedirs(LOCAL_DIR, exist_ok=True)

def sanitize(name):
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', " ", clean)
    return clean.strip()[:100]

def normalize_str(s):
    return re.sub(r'[^a-zA-Z0-9]', '', (s or '').lower())

def get_koel_token():
    try:
        r = requests.post(f"{KOEL_URL}/api/me", json={"email": "admin@rohan.run.place", "password": "__REDACTED__"}, timeout=15)
        if r.status_code == 200:
            return r.json().get("token")
    except Exception as e:
        print(f"[Koel API] Login error: {e}", flush=True)
    return None

def fetch_lyrics(track_name, artist_name):
    headers = {"User-Agent": "KoelMusic/1.0"}
    clean_artist = artist_name.split(",")[0].strip()
    clean_title = re.sub(r'\(feat\..*?\)', '', track_name, flags=re.I).strip()
    clean_title = re.sub(r'- .*', '', clean_title).strip()

    # 1. Exact get
    try:
        r = requests.get("https://lrclib.net/api/get", params={"track_name": track_name, "artist_name": clean_artist}, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            lyrics = data.get("syncedLyrics") or data.get("plainLyrics")
            if lyrics:
                return lyrics
    except Exception:
        pass

    # 2. Try clean title get
    if clean_title != track_name:
        try:
            r = requests.get("https://lrclib.net/api/get", params={"track_name": clean_title, "artist_name": clean_artist}, headers=headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                lyrics = data.get("syncedLyrics") or data.get("plainLyrics")
                if lyrics:
                    return lyrics
        except Exception:
            pass

    # 3. Search fallback
    try:
        q = f"{clean_artist} {clean_title}"
        r = requests.get("https://lrclib.net/api/search", params={"q": q}, headers=headers, timeout=6)
        if r.status_code == 200:
            results = r.json()
            if isinstance(results, list):
                for item in results:
                    lyrics = item.get("syncedLyrics") or item.get("plainLyrics")
                    if lyrics:
                        return lyrics
    except Exception:
        pass

    return ""

def apply_metadata(local_mp3, item, lyrics=""):
    track_name = item.get("track_name", "").strip()
    artist_name = item.get("artist_name", "").strip()
    album_name = item.get("album_name", "").strip()
    release_date = item.get("release_date", "").strip()
    image_url = item.get("image_url", "").strip()
    track_num = item.get("track_num", "").strip()
    disc_num = item.get("disc_num", "").strip()

    try:
        try:
            tags = ID3(local_mp3)
        except ID3NoHeaderError:
            tags = ID3()

        tags['TIT2'] = TIT2(encoding=3, text=track_name)
        tags['TPE1'] = TPE1(encoding=3, text=artist_name)
        tags['TALB'] = TALB(encoding=3, text=album_name)
        if release_date:
            tags['TDRC'] = TDRC(encoding=3, text=release_date[:4])
        if track_num:
            tags['TRCK'] = TRCK(encoding=3, text=str(track_num))
        if disc_num:
            tags['TPOS'] = TPOS(encoding=3, text=str(disc_num))

        if lyrics:
            tags['USLT'] = USLT(encoding=3, lang='eng', desc='', text=lyrics)

        if image_url and image_url.startswith("http") and 'APIC:' not in tags:
            try:
                r = requests.get(image_url, timeout=10)
                if r.status_code == 200:
                    tags['APIC'] = APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=r.content
                    )
            except Exception:
                pass

        tags.save(local_mp3, v2_version=3)
    except Exception as e:
        print(f"Warning: could not tag {local_mp3}: {e}", flush=True)

def cleanup_disk_space():
    try:
        free_bytes = shutil.disk_usage("C:").free
        free_gb = free_bytes / (1024**3)
        if free_gb < 8.0:
            print(f"[Disk Watchdog] C: drive has {free_gb:.1f} GB free (< 8 GB). Pruning local cache...", flush=True)
            # Remove local mp3 files in LOCAL_DIR that are older than 10 mins
            now = time.time()
            for fn in os.listdir(LOCAL_DIR):
                if fn.endswith(".mp3"):
                    fp = os.path.join(LOCAL_DIR, fn)
                    if now - os.path.getmtime(fp) > 600:
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
    except Exception as e:
        print(f"[Disk Watchdog] Error: {e}", flush=True)

def sync_koel_and_update_all_playlists(catalog):
    print("\n--- [Sync] Triggering Koel Library Sync ---", flush=True)
    try:
        subprocess.run(["ssh", "micro-2", "sudo docker exec koel php artisan koel:sync"], check=False, timeout=180)
    except Exception as e:
        print(f"[Koel Sync] Error: {e}", flush=True)

    token = get_koel_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        print("--- [Playlists] Mapping songs to playlists in Koel ---", flush=True)
        # Fetch all songs across all pages
        server_songs = {}
        url = f"{KOEL_URL}/api/songs"
        while url:
            res = requests.get(url, headers=headers, timeout=20).json()
            for s in res.get("data", []):
                norm_key = normalize_str(s.get("artist_name")) + "::" + normalize_str(s.get("title"))
                server_songs[norm_key] = s["id"]
            url = res.get("links", {}).get("next")

        print(f"[Playlists] Indexed {len(server_songs)} songs from Koel database.", flush=True)

        # For each playlist, find songs and add only missing ones
        playlists = catalog.get("playlists", {})
        tracks = catalog.get("tracks", {})

        # Build map: playlist_id -> list of song_ids
        playlist_targets = {}
        for key, item in tracks.items():
            if item.get("status") == "uploaded":
                norm_key = normalize_str(item.get("artist_name")) + "::" + normalize_str(item.get("track_name"))
                sid = server_songs.get(norm_key)
                if sid:
                    for pid in item.get("playlist_ids", []):
                        if pid not in playlist_targets:
                            playlist_targets[pid] = set()
                        playlist_targets[pid].add(sid)

        for pname, pid in playlists.items():
            needed_ids = playlist_targets.get(pid, set())
            if not needed_ids:
                continue
            # Get existing songs in playlist
            try:
                pr = requests.get(f"{KOEL_URL}/api/playlists/{pid}/songs", headers=headers, timeout=15)
                existing_in_p = set()
                if pr.status_code == 200:
                    p_data = pr.json()
                    existing_in_p = {s["id"] for s in (p_data.get("data") if isinstance(p_data, dict) else p_data)}

                to_add = list(needed_ids - existing_in_p)
                if to_add:
                    # Add in batches of 50 to prevent lock timeouts
                    for chunk_start in range(0, len(to_add), 50):
                        chunk = to_add[chunk_start:chunk_start+50]
                        add_r = requests.post(f"{KOEL_URL}/api/playlists/{pid}/songs", headers=headers, json={"songs": chunk}, timeout=25)
                        if add_r.status_code == 200:
                            print(f"  + Added {len(chunk)} songs to '{pname}' (Total: {len(existing_in_p) + len(chunk)})", flush=True)
            except Exception as pe:
                print(f"  ! Error updating playlist '{pname}': {pe}", flush=True)

    except Exception as e:
        print(f"[Playlists] Error updating playlists: {e}", flush=True)

def process_track(index, total, key, item):
    track_name = item.get("track_name", "").strip()
    artist_name = item.get("artist_name", "").strip()

    if not track_name:
        return None

    safe_title = sanitize(track_name)
    safe_artist = sanitize(artist_name)
    filename = f"{safe_artist} - {safe_title}.mp3"
    stem = f"{safe_artist} - {safe_title}"
    local_mp3 = os.path.join(LOCAL_DIR, filename)
    local_lrc = os.path.join(LOCAL_DIR, f"{stem}.lrc")

    if item.get("status") == "uploaded":
        return f"[SKIP] Already uploaded: {filename}"

    # Also check if it was downloaded into next_level_music earlier
    alt_local = os.path.join(r"C:\Users\Wissen\Downloads\Spotify\next_level_music", filename)
    if os.path.exists(alt_local) and os.path.getsize(alt_local) > 300_000:
        local_mp3 = alt_local

    mp3_exists = os.path.exists(local_mp3) and os.path.getsize(local_mp3) > 300_000

    # If missing MP3, download via yt-dlp
    if not mp3_exists:
        query = f"ytsearch1:{artist_name} - {track_name} audio"
        temp_pattern = os.path.join(LOCAL_DIR, f"temp_{index}.%(ext)s")
        temp_mp3 = os.path.join(LOCAL_DIR, f"temp_{index}.mp3")

        if os.path.exists(temp_mp3):
            try:
                os.remove(temp_mp3)
            except Exception:
                pass

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "--match-filter", "duration <= 900 & !is_live",
            "--max-filesize", "50M",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "--cookies-from-browser", "firefox",
            "-o", temp_pattern,
            query
        ]

        try:
            res = subprocess.run(cmd, timeout=75, capture_output=True, text=True)
            if not os.path.exists(temp_mp3):
                err = (res.stderr or "").strip()[:80]
                # Cleanup partials
                for f in os.listdir(LOCAL_DIR):
                    if f.startswith(f"temp_{index}."):
                        try: os.remove(os.path.join(LOCAL_DIR, f))
                        except Exception: pass
                return f"[FAIL] Download failed: {filename} ({err})"
            os.replace(temp_mp3, local_mp3)
        except subprocess.TimeoutExpired:
            for f in os.listdir(LOCAL_DIR):
                if f.startswith(f"temp_{index}."):
                    try: os.remove(os.path.join(LOCAL_DIR, f))
                    except Exception: pass
            return f"[TIMEOUT] Download timed out: {filename}"
        except Exception as e:
            return f"[ERROR] Exception downloading {filename}: {e}"

    # Fetch Lyrics
    lyrics = ""
    if not os.path.exists(local_lrc) or os.path.getsize(local_lrc) < 10:
        lyrics = fetch_lyrics(track_name, artist_name)
        if lyrics:
            try:
                with open(local_lrc, "w", encoding="utf-8") as lf:
                    lf.write(lyrics)
            except Exception:
                pass
    else:
        try:
            with open(local_lrc, "r", encoding="utf-8") as lf:
                lyrics = lf.read()
        except Exception:
            pass

    # Apply Metadata & Cover & Lyrics
    apply_metadata(local_mp3, item, lyrics)

    # Upload MP3 and LRC to micro-2 using legacy SCP (-O) for reliability
    try:
        subprocess.run(["scp", "-O", "-q", local_mp3, REMOTE_DEST], timeout=90, check=True)
        if os.path.exists(local_lrc):
            subprocess.run(["scp", "-O", "-q", local_lrc, REMOTE_DEST], timeout=60)
        item["status"] = "uploaded"
        cleanup_disk_space()
        has_lyr = "with lyrics" if lyrics else "no lyrics"
        return f"[DONE] {filename} ({has_lyr}, uploaded)"
    except Exception as e:
        return f"[DONE] {filename} (saved locally, upload retry pending: {e})"

def ensure_pot_server():
    try:
        r = requests.get("http://127.0.0.1:4416/ping", timeout=2)
        if r.status_code == 200:
            return
    except Exception:
        pass
    print("[POT Provider] Starting local BotGuard POT server...", flush=True)
    try:
        subprocess.Popen(
            [r"C:\Users\Wissen\bgutil-pot.exe", "server", "--host", "0.0.0.0", "--port", "4416"],
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
        time.sleep(2)
    except Exception as e:
        print(f"[POT Provider] Error starting POT server: {e}", flush=True)

def main():
    ensure_pot_server()
    if not os.path.exists(CATALOG_PATH):
        print(f"Error: {CATALOG_PATH} not found. Run build_full_catalog.py first!")
        sys.exit(1)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    tracks = catalog.get("tracks", {})
    total = len(tracks)
    pending_items = [(k, v) for k, v in tracks.items() if v.get("status") != "uploaded"]
    already_done = total - len(pending_items)

    print(f"============================================================", flush=True)
    print(f"=== MASTER SPOTIFY INGESTION: 56 Playlists ===", flush=True)
    print(f"Total Unique Tracks : {total}", flush=True)
    print(f"Already Completed   : {already_done}", flush=True)
    print(f"Remaining to Process: {len(pending_items)}", flush=True)
    print(f"============================================================\n", flush=True)

    completed_in_run = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_track, i+1, len(pending_items), key, item): (key, item) for i, (key, item) in enumerate(pending_items)}
        for future in as_completed(futures):
            key, item = futures[future]
            try:
                msg = future.result()
                if msg:
                    completed_in_run += 1
                    total_done = already_done + completed_in_run
                    print(f"[{total_done}/{total}] {msg}", flush=True)

                    # Persist catalog state every 15 items
                    if completed_in_run % 15 == 0:
                        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
                            json.dump(catalog, f, indent=2)

                    # Sync Koel and update playlists every 40 items
                    if completed_in_run % 40 == 0:
                        sync_koel_and_update_all_playlists(catalog)

            except Exception as e:
                print(f"Unhandled error for {key}: {e}", flush=True)

    print("=== All downloads finished! Running final sync & playlist update ===", flush=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    sync_koel_and_update_all_playlists(catalog)
    print("=== Full Catalog Ingestion Complete! ===", flush=True)

if __name__ == "__main__":
    main()
