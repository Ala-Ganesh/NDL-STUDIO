from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
import json
import os
import sqlite3
import time

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "channel.json"
CONTENT_FILE = DATA_DIR / "content.json"
DB_FILE = DATA_DIR / "ndl_studios.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ndl-local-development-secret-change-me")


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp.replace(path)


def load_channel():
    return load_json(DATA_FILE, {"channel": {}, "programs": [], "poll": {"question": "", "options": {}}})


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                option TEXT NOT NULL,
                voted_at TEXT NOT NULL
            )
        """)
        conn.commit()


def poll_counts(channel):
    options = channel.get("poll", {}).get("options", {})
    counts = {name: 0 for name in options}
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute("SELECT option, COUNT(*) FROM poll_votes GROUP BY option").fetchall()
    for option, count in rows:
        if option in counts:
            counts[option] = count
    return counts


def channel_payload():
    channel = load_channel()
    channel.setdefault("poll", {})["options"] = poll_counts(channel)
    return channel


def get_program_state(channel, now=None):
    programs = channel.get("programs", [])
    if not programs:
        return {"current_index": None, "next_index": None, "elapsed": 0, "remaining": 0, "total": 0}

    now = time.time() if now is None else now
    total_cycle = sum(max(1, int(p.get("duration_seconds", 60))) for p in programs)
    position = now % total_cycle
    elapsed_before = 0
    for index, program in enumerate(programs):
        duration = max(1, int(program.get("duration_seconds", 60)))
        if position < elapsed_before + duration:
            elapsed = position - elapsed_before
            remaining = duration - elapsed
            next_index = (index + 1) % len(programs)
            start_epoch = now - elapsed
            return {
                "current_index": index,
                "next_index": next_index,
                "elapsed": round(elapsed, 1),
                "remaining": round(remaining, 1),
                "total": duration,
                "start_epoch": start_epoch,
                "end_epoch": start_epoch + duration,
            }
        elapsed_before += duration

    return {"current_index": 0, "next_index": 1 % len(programs), "elapsed": 0, "remaining": programs[0].get("duration_seconds", 60), "total": programs[0].get("duration_seconds", 60)}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/channel")
def channel():
    data = channel_payload()
    state = get_program_state(data)
    data["state"] = state
    data["server_time"] = datetime.now(timezone.utc).isoformat()
    return jsonify(data)


@app.route("/api/channel/state")
def channel_state():
    data = channel_payload()
    state = get_program_state(data)
    programs = data.get("programs", [])
    state["current"] = programs[state["current_index"]] if state["current_index"] is not None else None
    state["next"] = programs[state["next_index"]] if state["next_index"] is not None else None
    state["server_epoch"] = time.time()
    return jsonify(state)


@app.route("/api/poll", methods=["POST"])
def poll():
    data = load_channel()
    payload = request.get_json(silent=True) or {}
    option = payload.get("option")
    options = data.get("poll", {}).get("options", {})
    if option not in options:
        return jsonify({"ok": False, "error": "Invalid poll option"}), 400
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO poll_votes (option, voted_at) VALUES (?, ?)", (option, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return jsonify({"ok": True, "poll": {"question": data["poll"].get("question", ""), "options": poll_counts(data)}})


@app.route("/api/health")
def health():
    data = load_channel()
    return jsonify({
        "status": "ONLINE",
        "channel": data.get("channel", {}).get("name", "NDL STUDIOS"),
        "mode": data.get("channel", {}).get("mode", "SIMULATED-LIVE"),
        "server_time": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/sitemap.xml")
def sitemap():
    return render_template("sitemap.xml"), 200, {"Content-Type": "application/xml; charset=utf-8"}


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = os.environ.get("ADMIN_PASSWORD")
        if not expected and os.environ.get("FLASK_DEBUG", "1") != "1":
            return render_template("admin_login.html", error="ADMIN_PASSWORD is not configured on this server."), 503
        expected = expected or "admin"
        if password and password == expected:
            session["admin_authenticated"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid admin password."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    data = channel_payload()
    content = load_json(CONTENT_FILE, [])
    return render_template("admin.html", channel=data, content=content)


@app.route("/api/admin/programs", methods=["POST"])
@admin_required
def admin_programs():
    data = load_channel()
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    if not title:
        return jsonify({"ok": False, "error": "Programme title is required."}), 400
    duration = max(1, int(payload.get("duration_seconds", 60)))
    program = {
        "id": max([int(p.get("id", 0)) for p in data.get("programs", [])] or [0]) + 1,
        "title": title,
        "type": str(payload.get("type", "Programme")).strip() or "Programme",
        "duration_seconds": duration,
        "video": str(payload.get("video", "/static/media/ndl_broadcast_test.mp4")).strip(),
        "description": str(payload.get("description", "")).strip(),
    }
    data.setdefault("programs", []).append(program)
    save_json(DATA_FILE, data)
    return jsonify({"ok": True, "program": program})


@app.route("/api/admin/programs/<int:program_id>", methods=["PUT"])
@admin_required
def admin_update_program(program_id):
    data = load_channel()
    payload = request.get_json(silent=True) or {}
    program = next((p for p in data.get("programs", []) if int(p.get("id", -1)) == program_id), None)
    if program is None:
        return jsonify({"ok": False, "error": "Programme not found."}), 404

    title = str(payload.get("title", program.get("title", ""))).strip()
    if not title:
        return jsonify({"ok": False, "error": "Programme title is required."}), 400
    try:
        duration = max(1, int(payload.get("duration_seconds", program.get("duration_seconds", 60))))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Duration must be a valid number."}), 400

    program.update({
        "title": title,
        "type": str(payload.get("type", program.get("type", "Programme"))).strip() or "Programme",
        "duration_seconds": duration,
        "video": str(payload.get("video", program.get("video", "/static/media/ndl_broadcast_test.mp4"))).strip(),
        "description": str(payload.get("description", program.get("description", ""))).strip(),
    })
    save_json(DATA_FILE, data)
    return jsonify({"ok": True, "program": program})


@app.route("/api/admin/programs/reorder", methods=["POST"])
@admin_required
def admin_reorder_programs():
    data = load_channel()
    payload = request.get_json(silent=True) or {}
    ordered_ids = payload.get("ids", [])
    programs = data.get("programs", [])
    if not isinstance(ordered_ids, list) or len(ordered_ids) != len(programs):
        return jsonify({"ok": False, "error": "Send every programme ID in the new order."}), 400

    try:
        ordered_ids = [int(value) for value in ordered_ids]
        by_id = {int(p.get("id")): p for p in programs}
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Programme IDs must be numeric."}), 400

    if set(ordered_ids) != set(by_id):
        return jsonify({"ok": False, "error": "The new order does not match the current programmes."}), 400

    data["programs"] = [by_id[program_id] for program_id in ordered_ids]
    save_json(DATA_FILE, data)
    return jsonify({"ok": True, "programs": data["programs"]})


@app.route("/api/admin/programs/<int:program_id>", methods=["DELETE"])
@admin_required
def admin_delete_program(program_id):
    data = load_channel()
    before = len(data.get("programs", []))
    data["programs"] = [p for p in data.get("programs", []) if int(p.get("id", -1)) != program_id]
    if len(data["programs"]) == 0:
        return jsonify({"ok": False, "error": "Keep at least one programme in the channel."}), 400
    if len(data["programs"]) == before:
        return jsonify({"ok": False, "error": "Programme not found."}), 404
    save_json(DATA_FILE, data)
    return jsonify({"ok": True})


@app.route("/api/admin/content", methods=["POST"])
@admin_required
def admin_add_content():
    content = load_json(CONTENT_FILE, [])
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    if not title:
        return jsonify({"ok": False, "error": "Content title is required."}), 400
    rights = str(payload.get("rights_status", "PENDING REVIEW")).strip().upper() or "PENDING REVIEW"
    allowed_rights = {"VERIFIED", "PENDING REVIEW", "ORIGINAL", "PUBLIC DOMAIN", "LICENSED", "NOT CLEARED"}
    if rights not in allowed_rights:
        return jsonify({"ok": False, "error": "Invalid rights status."}), 400
    item = {
        "title": title,
        "type": str(payload.get("type", "Programme")).strip() or "Programme",
        "year": str(payload.get("year", "")).strip(),
        "duration": str(payload.get("duration", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "thumbnail": str(payload.get("thumbnail", "")).strip(),
        "video": str(payload.get("video", "")).strip(),
        "rights_status": rights,
        "source": str(payload.get("source", "")).strip(),
    }
    content.append(item)
    save_json(CONTENT_FILE, content)
    return jsonify({"ok": True, "item": item})


@app.route("/api/admin/poll/reset", methods=["POST"])
@admin_required
def admin_reset_poll():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM poll_votes")
        conn.commit()
    return jsonify({"ok": True})


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print("\n==============================================")
    print("  NDL STUDIOS - LINEAR STREAMING CHANNEL")
    print("  Local Broadcast Prototype")
    print(f"  http://127.0.0.1:{port}")
    print("==============================================\n")
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "1") == "1")
