import os
import glob
import csv
import json
import requests

KOEL_URL = "https://koel.rohan.run.place"
PLAYLISTS_DIR = r"C:\Users\Wissen\Downloads\Spotify\playlists"
CATALOG_PATH = r"C:\Users\Wissen\Downloads\Spotify\master_catalog.json"
LOCAL_MUSIC_DIR = r"C:\Users\Wissen\Downloads\Spotify\next_level_music"

print("=== Authenticating with Koel ===", flush=True)
r = requests.post(f"{KOEL_URL}/api/me", json={"email": "admin@rohan.run.place", "password": "__REDACTED__"}, timeout=15)
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# 1. Fetch or create all playlists in Koel
print("=== Ensuring all 56 playlists exist in Koel ===", flush=True)
existing_playlists = {p['name'].lower(): p['id'] for p in requests.get(f"{KOEL_URL}/api/playlists", headers=headers, timeout=15).json()}
csv_files = glob.glob(os.path.join(PLAYLISTS_DIR, "*.csv"))

playlist_id_map = {} # Title -> id
for cp in csv_files:
    fname = os.path.basename(cp)
    pname = os.path.splitext(fname)[0].replace('_', ' ').strip().title()
    if pname.lower() in existing_playlists:
        playlist_id_map[pname] = existing_playlists[pname.lower()]
    else:
        cr = requests.post(f"{KOEL_URL}/api/playlists", headers=headers, json={"name": pname}, timeout=15)
        if cr.status_code == 201:
            pid = cr.json()["id"]
            playlist_id_map[pname] = pid
            existing_playlists[pname.lower()] = pid
            print(f"Created playlist: {pname} -> {pid}", flush=True)
        else:
            print(f"Failed to create playlist {pname}: {cr.status_code}", flush=True)

print(f"Total playlists registered in Koel: {len(playlist_id_map)}", flush=True)

# 2. Collect and deduplicate all songs across all CSVs
print("=== Aggregating all tracks across 56 playlists ===", flush=True)
unique_tracks = {} # key -> dict
total_entries = 0

for cp in csv_files:
    fname = os.path.basename(cp)
    pname = os.path.splitext(fname)[0].replace('_', ' ').strip().title()
    pid = playlist_id_map.get(pname)
    try:
        with open(cp, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                track = row.get("Track Name", "").strip()
                artist = row.get("Artist Name(s)", "").strip()
                if not track:
                    continue
                total_entries += 1
                key = f"{artist.lower()} - {track.lower()}"
                if key not in unique_tracks:
                    unique_tracks[key] = {
                        "track_name": track,
                        "artist_name": artist,
                        "album_name": row.get("Album Name", "").strip(),
                        "release_date": row.get("Album Release Date", "").strip(),
                        "image_url": row.get("Album Image URL", "").strip(),
                        "track_num": row.get("Track Number", "").strip(),
                        "disc_num": row.get("Disc Number", "").strip(),
                        "playlist_names": [pname],
                        "playlist_ids": [pid] if pid else [],
                        "status": "pending"
                    }
                else:
                    if pname not in unique_tracks[key]["playlist_names"]:
                        unique_tracks[key]["playlist_names"].append(pname)
                        if pid and pid not in unique_tracks[key]["playlist_ids"]:
                            unique_tracks[key]["playlist_ids"].append(pid)
    except Exception as e:
        print(f"Error parsing {fname}: {e}", flush=True)

# 3. Check what's already downloaded locally in next_level_music
already_downloaded = 0
for key, item in unique_tracks.items():
    safe_title = "".join(c for c in item["track_name"] if c not in r'\/*?:"<>|')[:100].strip()
    safe_artist = "".join(c for c in item["artist_name"] if c not in r'\/*?:"<>|')[:100].strip()
    fn = f"{safe_artist} - {safe_title}.mp3"
    lp = os.path.join(LOCAL_MUSIC_DIR, fn)
    if os.path.exists(lp) and os.path.getsize(lp) > 300_000:
        item["status"] = "uploaded"
        already_downloaded += 1

print(f"Total entries across all playlists: {total_entries}", flush=True)
print(f"Total unique tracks: {len(unique_tracks)}", flush=True)
print(f"Already downloaded & verified: {already_downloaded}", flush=True)
print(f"Remaining unique tracks to download: {len(unique_tracks) - already_downloaded}", flush=True)

catalog = {
    "playlists": playlist_id_map,
    "tracks": unique_tracks
}

with open(CATALOG_PATH, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2)

print(f"Master catalog saved to: {CATALOG_PATH}", flush=True)
