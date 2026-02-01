# -*- coding: utf-8 -*-
"""가족 통합 일정표 웹 대시보드 - Flask + DB(PostgreSQL)"""
import os
import json
import time
from flask import Flask, render_template, request, jsonify

# DB 사용 여부: DATABASE_URL 이 있으면 PostgreSQL, 없으면 JSON 파일 사용
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
DATA_PATH = os.path.join(BASE_DIR, "family_pro_data.json")

app = Flask(__name__, template_folder=TEMPLATES_DIR)

MEMBERS = {
    "아빠": "#BBDEFB",
    "엄마": "#F8BBD0",
    "수현": "#FFE0B2",
    "태현": "#C8E6C9"
}
DAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]
TIMES = [f"{h:02d}:00" for h in range(6, 25)]

# ----- DB 사용 시 -----
db_engine = None
if DATABASE_URL:
    try:
        from sqlalchemy import create_engine, Column, Integer, String, text
        from sqlalchemy.orm import sessionmaker, declarative_base
        Base = declarative_base()
        class CalendarEvent(Base):
            __tablename__ = "calendar_events"
            id = Column(Integer, primary_key=True, autoincrement=True)
            slot_key = Column(String(32), nullable=False)
            text = Column(String(512), nullable=False)
            bg = Column(String(32), nullable=False)
            who = Column(String(32), nullable=False)
            event_id = Column(String(64), nullable=False)
            memo = Column(String(512), nullable=True)
        db_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(db_engine)
        Session = sessionmaker(bind=db_engine)
    except Exception as e:
        db_engine = None
        print("DB init failed, using JSON:", e)


def load_data():
    if db_engine:
        try:
            session = Session()
            rows = session.query(CalendarEvent).order_by(CalendarEvent.slot_key, CalendarEvent.id).all()
            data = {}
            for r in rows:
                key = r.slot_key
                if key not in data:
                    data[key] = []
                ev = {"text": r.text, "bg": r.bg, "who": r.who, "event_id": r.event_id or None}
                if getattr(r, "memo", None):
                    ev["memo"] = r.memo
                data[key].append(ev)
            session.close()
            return data
        except Exception as e:
            print("DB load error:", e)
            return {}
    # JSON fallback
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


def parse_end_row(end_str, start_row):
    """종료 시간(예: 16) → 16시에 종료. 채울 슬롯은 range(start_row, end_row)로 end_row 미포함."""
    if not end_str or not str(end_str).strip():
        return start_row + 1
    end_str = str(end_str).strip()
    for i, t in enumerate(TIMES):
        if end_str == t or end_str.startswith(t[:2]):
            if i <= start_row:
                return start_row + 1
            return i
    try:
        h = int(end_str)
        if 6 <= h <= 24:
            idx = h - 6
            if idx <= start_row:
                return start_row + 1
            return idx
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
    payload = request.get_json() or {}
    date_str = payload.get("date_str")
    time_index = int(payload.get("time_index", 0))
    end_time_input = payload.get("end_time", "").strip()
    who = payload.get("who", "아빠")
    content = payload.get("content", "").strip()
    memo = payload.get("memo", "").strip()

    if not date_str or content is None or time_index < 0 or time_index >= len(TIMES):
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    if who not in MEMBERS:
        who = "아빠"

    end_row = parse_end_row(end_time_input, time_index)
    end_row = min(end_row, len(TIMES))

    event_id = str(time.time()).replace(".", "_")
    time_str = TIMES[time_index]
    end_display = TIMES[end_row - 1] if end_row > time_index + 1 else None
    display_text = f"{who}: {content}"
    if end_display and end_display != time_str:
        display_text = f"{who}: {content} ({time_str}~{end_display})"

    if db_engine:
        try:
            session = Session()
            for r in range(time_index, end_row):
                key = f"{date_str}_{TIMES[r]}"
                ev = CalendarEvent(slot_key=key, text=display_text, bg=MEMBERS[who], who=who, event_id=event_id, memo=memo or None)
                session.add(ev)
            session.commit()
            session.close()
            return jsonify({"ok": True, "data": load_data()})
        except Exception as e:
            if session:
                session.rollback()
                session.close()
            return jsonify({"ok": False, "error": str(e)}), 500

    # JSON fallback
    data = load_data()
    new_entry = {"text": display_text, "bg": MEMBERS[who], "who": who, "event_id": event_id}
    if memo:
        new_entry["memo"] = memo
    for r in range(time_index, end_row):
        key = f"{date_str}_{TIMES[r]}"
        if key not in data or not isinstance(data[key], list):
            data[key] = []
        data[key].append(new_entry.copy())
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({"ok": True, "data": load_data()})


@app.route("/api/event/delete", methods=["POST"])
def api_delete_event():
    payload = request.get_json() or {}
    key = payload.get("key")
    index = payload.get("index", -1)
    event_id = payload.get("event_id")

    if db_engine:
        try:
            session = Session()
            eid = event_id
            if not eid and key is not None and 0 <= index:
                data = load_data()
                if key in data and isinstance(data[key], list) and 0 <= index < len(data[key]):
                    eid = data[key][index].get("event_id")
            if eid:
                session.query(CalendarEvent).filter(CalendarEvent.event_id == eid).delete()
            session.commit()
            session.close()
            return jsonify({"ok": True, "data": load_data()})
        except Exception as e:
            if session:
                session.rollback()
                session.close()
            return jsonify({"ok": False, "error": str(e)}), 500

    data = load_data()
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
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({"ok": True, "data": load_data()})


@app.route("/api/event/update", methods=["POST"])
def api_update_event():
    payload = request.get_json() or {}
    key = payload.get("key")
    index = payload.get("index", -1)
    event_id = payload.get("event_id")
    content = payload.get("content", "").strip()
    who = payload.get("who", "아빠")
    memo = payload.get("memo", "").strip()
    date_str = payload.get("date_str")
    start_time_index = payload.get("start_time_index")
    end_time_input = payload.get("end_time", "").strip()

    if who not in MEMBERS:
        who = "아빠"
    if not content:
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    def new_text(ev_text):
        time_suffix = ""
        if " (" in ev_text and "~" in ev_text and ")" in ev_text:
            idx = ev_text.rfind(" (")
            if idx >= 0:
                time_suffix = ev_text[idx:]
        return f"{who}: {content}{time_suffix}"

    # 시간 변경: 삭제 후 새 시간대로 추가
    if event_id and date_str is not None and start_time_index is not None and db_engine:
        end_row = parse_end_row(end_time_input, start_time_index)
        end_row = min(end_row, len(TIMES))
        time_str = TIMES[start_time_index]
        end_display = TIMES[end_row - 1] if (end_row > start_time_index and end_row <= len(TIMES)) else None
        display_text = f"{who}: {content}"
        if end_display and end_display != time_str:
            display_text = f"{who}: {content} ({time_str}~{end_display})"
        try:
            session = Session()
            session.query(CalendarEvent).filter(CalendarEvent.event_id == event_id).delete()
            for r in range(start_time_index, end_row):
                slot_key = f"{date_str}_{TIMES[r]}"
                ev = CalendarEvent(slot_key=slot_key, text=display_text, bg=MEMBERS[who], who=who, event_id=event_id, memo=memo or None)
                session.add(ev)
            session.commit()
            session.close()
            return jsonify({"ok": True, "data": load_data()})
        except Exception as e:
            if session:
                session.rollback()
                session.close()
            return jsonify({"ok": False, "error": str(e)}), 500

    if db_engine:
        try:
            session = Session()
            eid = event_id
            if not eid and key is not None and 0 <= index:
                data = load_data()
                if key in data and isinstance(data[key], list) and 0 <= index < len(data[key]):
                    eid = data[key][index].get("event_id")
            if eid:
                rows = session.query(CalendarEvent).filter(CalendarEvent.event_id == eid).all()
                for r in rows:
                    r.text = new_text(r.text)
                    r.who = who
                    r.bg = MEMBERS[who]
                    r.memo = memo or None
                session.commit()
            session.close()
            return jsonify({"ok": True, "data": load_data()})
        except Exception as e:
            if session:
                session.rollback()
                session.close()
            return jsonify({"ok": False, "error": str(e)}), 500

    data = load_data()
    def upd(ev, c, w, m):
        ev["text"] = new_text(ev.get("text", ""))
        ev["who"] = w
        ev["bg"] = MEMBERS[w]
        if "memo" in ev or m:
            ev["memo"] = m
    if event_id:
        for k in list(data.keys()):
            if not isinstance(data.get(k), list):
                continue
            for ev in data[k]:
                if ev.get("event_id") == event_id:
                    upd(ev, content, who, memo)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
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
                        upd(e, content, who, memo)
        else:
            upd(ev, content, who, memo)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return jsonify({"ok": True, "data": load_data()})

    return jsonify({"ok": False, "error": "invalid_input"}), 400


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    print("")
    print("=" * 50)
    print("  Family Calendar Web - Server starting")
    print("  DB:", "PostgreSQL" if DATABASE_URL else "JSON file")
    print("  Open: http://127.0.0.1:%s" % PORT)
    print("=" * 50)
    print("")
    app.run(host="0.0.0.0", port=PORT, debug=True)
