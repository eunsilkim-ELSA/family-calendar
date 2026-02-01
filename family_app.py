# -*- coding: utf-8 -*-
"""가족 통합 일정표 웹 대시보드 - Flask 서버"""
import os
import json
import time
from flask import Flask, render_template, request, jsonify

# templates 폴더 경로를 family_app.py와 같은 위치로 고정 (Render 등에서 오류 방지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)

MEMBERS = {
    "아빠": "#BBDEFB",
    "엄마": "#F8BBD0",
    "수현": "#FFE0B2",
    "태현": "#C8E6C9"
}
DAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]
TIMES = [f"{h:02d}:00" for h in range(6, 25)]

DATA_PATH = os.path.join(BASE_DIR, "family_pro_data.json")


def load_data():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data and not isinstance(next(iter(data.values()), []), list):
                return {}
            return data
    except Exception:
        return {}


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def parse_end_row(end_str, start_row):
    if not end_str or not str(end_str).strip():
        return start_row + 1
    end_str = str(end_str).strip()
    for i, t in enumerate(TIMES):
        if end_str == t or end_str.startswith(t[:2]):
            if i <= start_row:
                return start_row + 1
            return i + 1
    try:
        h = int(end_str)
        if 6 <= h <= 24:
            idx = h - 6
            if idx <= start_row:
                return start_row + 1
            return idx + 1
    except ValueError:
        pass
    return start_row + 1


@app.route("/")
def index():
    return render_template("index.html", members=MEMBERS, days_kr=DAYS_KR, times=TIMES)


@app.route("/api/data", methods=["GET"])
def api_get_data():
    return jsonify(load_data())


@app.route("/api/event", methods=["POST"])
def api_add_event():
    data = load_data()
    payload = request.get_json() or {}
    date_str = payload.get("date_str")
    time_index = int(payload.get("time_index", 0))
    end_time_input = payload.get("end_time", "").strip()
    who = payload.get("who", "아빠")
    content = payload.get("content", "").strip()

    if not date_str or content is None or time_index < 0 or time_index >= len(TIMES):
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    if who not in MEMBERS:
        who = "아빠"

    end_row = parse_end_row(end_time_input, time_index)
    end_row = min(end_row, len(TIMES))

    event_id = str(time.time()) if end_row > time_index + 1 else None
    time_str = TIMES[time_index]
    end_display = TIMES[end_row - 1] if end_row > time_index + 1 else None
    display_text = f"{who}: {content}"
    if end_display and end_display != time_str:
        display_text = f"{who}: {content} ({time_str}~{end_display})"

    new_entry = {"text": display_text, "bg": MEMBERS[who], "who": who}
    if event_id:
        new_entry["event_id"] = event_id

    for r in range(time_index, end_row):
        key = f"{date_str}_{TIMES[r]}"
        if key not in data or not isinstance(data[key], list):
            data[key] = []
        data[key].append(new_entry.copy())

    save_data(data)
    return jsonify({"ok": True, "data": load_data()})


@app.route("/api/event/delete", methods=["POST"])
def api_delete_event():
    data = load_data()
    payload = request.get_json() or {}
    key = payload.get("key")
    index = payload.get("index", -1)
    event_id = payload.get("event_id")

    if event_id:
        for k in list(data.keys()):
            if not isinstance(data.get(k), list):
                continue
            data[k] = [e for e in data[k] if e.get("event_id") != event_id]
            if not data[k]:
                del data[k]
    elif key and key in data and isinstance(data[key], list) and 0 <= index < len(data[key]):
        event = data[key][index]
        eid = event.get("event_id") if isinstance(event, dict) else None
        if eid:
            for k in list(data.keys()):
                if not isinstance(data.get(k), list):
                    continue
                data[k] = [e for e in data[k] if e.get("event_id") != eid]
                if not data[k]:
                    del data[k]
        else:
            del data[key][index]
            if not data[key]:
                del data[key]
    else:
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    save_data(data)
    return jsonify({"ok": True, "data": load_data()})


@app.route("/api/event/update", methods=["POST"])
def api_update_event():
    data = load_data()
    payload = request.get_json() or {}
    key = payload.get("key")
    index = payload.get("index", -1)
    event_id = payload.get("event_id")
    content = payload.get("content", "").strip()
    who = payload.get("who", "아빠")

    if who not in MEMBERS:
        who = "아빠"
    if not content:
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    def update_event_text_bg(ev, new_content, new_who):
        # 기존 시간대 문자열 유지 (예: " (09:00~12:00)")
        text = ev.get("text", "")
        time_suffix = ""
        if " (" in text and "~" in text and ")" in text:
            idx = text.rfind(" (")
            if idx >= 0:
                time_suffix = text[idx:]
        ev["text"] = f"{new_who}: {new_content}{time_suffix}"
        ev["who"] = new_who
        ev["bg"] = MEMBERS[new_who]

    if event_id:
        for k in list(data.keys()):
            if not isinstance(data.get(k), list):
                continue
            for ev in data[k]:
                if ev.get("event_id") == event_id:
                    update_event_text_bg(ev, content, who)
        save_data(data)
        return jsonify({"ok": True, "data": load_data()})

    if key and key in data and isinstance(data[key], list) and 0 <= index < len(data[key]):
        ev = data[key][index]
        eid = ev.get("event_id")
        if eid:
            for k in list(data.keys()):
                if not isinstance(data.get(k), list):
                    continue
                for e in data[k]:
                    if e.get("event_id") == eid:
                        update_event_text_bg(e, content, who)
        else:
            update_event_text_bg(ev, content, who)
        save_data(data)
        return jsonify({"ok": True, "data": load_data()})

    return jsonify({"ok": False, "error": "invalid_input"}), 400


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    print("")
    print("=" * 50)
    print("  Family Calendar Web - Server starting")
    print("  Open in browser: http://127.0.0.1:%s" % PORT)
    print("=" * 50)
    print("")
    app.run(host="0.0.0.0", port=PORT, debug=True)