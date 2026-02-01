import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime, timedelta
import json
import math
import os  # 경로 설정을 위해 추가됨

# 1. 가족 구성원 설정
MEMBERS = {
    "아빠": "#BBDEFB", 
    "엄마": "#F8BBD0", 
    "첫째": "#FFE0B2", 
    "둘째": "#C8E6C9"
}
DAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]
TIMES = [f"{h:02d}:00" for h in range(6, 25)]

class FamilyCalendar:
    def __init__(self, root):
        self.root = root
        self.root.title("우리 가족 통합 일정표 v14.0")
        self.root.geometry("1200x950")
        
        # 파일 경로 설정 (이 부분이 수정되었습니다)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(current_dir, "family_pro_data.json")

        # 오늘 기준 일요일 계산
        today = datetime.now()
        offset = (today.weekday() + 1) % 7
        self.view_date = (today - timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 선택 변수
        self.selected_member = tk.StringVar(value="아빠")
        
        self.data = self.load_data()
        self.setup_ui()
        self.refresh_view()

    def setup_ui(self):
        # 상단바
        top_frame = tk.Frame(self.root, bg="#2C3E50", pady=10)
        top_frame.pack(fill="x")

        # 네비게이션
        nav_frame = tk.Frame(top_frame, bg="#2C3E50")
        nav_frame.pack(side="left", padx=20)
        
        tk.Button(nav_frame, text="<<", command=self.prev_month).pack(side="left", padx=2)
        tk.Button(nav_frame, text="<", command=self.prev_week).pack(side="left", padx=2)
        self.date_label = tk.Label(nav_frame, text="", font=("Arial", 15, "bold"), fg="white", bg="#2C3E50", width=22)
        self.date_label.pack(side="left", padx=10)
        tk.Button(nav_frame, text=">", command=self.next_week).pack(side="left", padx=2)
        tk.Button(nav_frame, text=">>", command=self.next_month).pack(side="left", padx=2)

        # 멤버 선택 버튼
        ctrl_frame = tk.Frame(top_frame, bg="#2C3E50")
        ctrl_frame.pack(side="right", padx=20)

        tk.Label(ctrl_frame, text="작성자: ", fg="white", bg="#2C3E50").pack(side="left")
        for name, color in MEMBERS.items():
            tk.Radiobutton(ctrl_frame, text=name, variable=self.selected_member, value=name,
                           bg=color, indicatoron=0, width=6, font=("Arial", 9, "bold")).pack(side="left", padx=2)

    def refresh_view(self):
        if hasattr(self, 'container'): self.container.destroy()

        self.container = tk.Frame(self.root)
        self.container.pack(expand=True, fill="both")
        
        self.canvas = tk.Canvas(self.container, bg="white")
        self.scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.grid_frame = tk.Frame(self.canvas, bg="white")
        
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", expand=True, fill="both")
        self.scrollbar.pack(side="right", fill="y")

        # 주차 표시
        mid_week = self.view_date + timedelta(days=3)
        week_num = int(math.ceil((mid_week.day + (mid_week.replace(day=1).weekday() + 1) % 7) / 7.0))
        self.date_label.config(text=f"{mid_week.strftime('%Y년 %m월')} {week_num}주차")

        # 헤더
        for j, day in enumerate(DAYS_KR):
            d = self.view_date + timedelta(days=j)
            bg = "#F1C40F" if d.date() == datetime.now().date() else "#ECF0F1"
            tk.Label(self.grid_frame, text=f"{day}({d.strftime('%m/%d')})", font=("Arial", 10, "bold"), 
                     width=18, height=2, bg=bg, relief="ridge").grid(row=0, column=j+1)

        # 시간표 본체
        for i, time in enumerate(TIMES):
            tk.Label(self.grid_frame, text=time, width=8, height=4, bg="#BDC3C7", relief="ridge").grid(row=i+1, column=0)
            
            for j in range(7):
                curr_d = (self.view_date + timedelta(days=j)).strftime("%Y-%m-%d")
                key = f"{curr_d}_{time}"
                
                # 셀 프레임
                cell = tk.Frame(self.grid_frame, bg="white", highlightthickness=0.5, highlightbackground="#ddd")
                cell.grid(row=i+1, column=j+1, sticky="nsew")
                
                # 일정이 있으면 버튼으로 추가
                if key in self.data:
                    for idx, ev in enumerate(self.data[key]):
                        if isinstance(ev, str): continue 
                        
                        btn = tk.Button(cell, text=ev["text"], bg=ev["bg"], font=("Arial", 8),
                                        relief="flat", anchor="w",
                                        command=lambda k=key, x=idx: self.delete_event(k, x))
                        btn.pack(fill="x", pady=1)
                
                # 칸 클릭 시 입력 창 띄우기
                cell.bind("<Button-1>", lambda e, r=i, c=j: self.add_event(r, c))

        self.grid_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def add_event(self, row, col):
        date_str = (self.view_date + timedelta(days=col)).strftime("%Y-%m-%d")
        time_str = TIMES[row]
        who = self.selected_member.get()
        
        content = simpledialog.askstring("입력", f"[{date_str} {time_str}] {who}님의 일정:")
        
        if content:
            key = f"{date_str}_{time_str}"
            if key not in self.data or not isinstance(self.data[key], list):
                self.data[key] = []
            
            # 새 데이터 추가
            new_entry = {
                "text": f"{who}: {content}",
                "bg": MEMBERS[who],
                "who": who
            }
            self.data[key].append(new_entry)
            self.save_data()
            self.refresh_view()

    def delete_event(self, key, index):
        if messagebox.askyesno("삭제", "선택한 일정을 삭제할까요?"):
            del self.data[key][index]
            if not self.data[key]: del self.data[key]
            self.save_data()
            self.refresh_view()

    def save_data(self):
        # 수정된 부분: self.file_path 사용
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("저장 오류", f"파일을 저장할 수 없습니다.\n{e}")

    def load_data(self):
        # 수정된 부분: self.file_path 사용 및 파일 없을 시 자동 생성 처리
        if not os.path.exists(self.file_path):
            return {}
            
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                return content if isinstance(next(iter(content.values()), []), list) else {}
        except: 
            return {}

    def prev_week(self): self.view_date -= timedelta(days=7); self.refresh_view()
    def next_week(self): self.view_date += timedelta(days=7); self.refresh_view()
    def prev_month(self): self.view_date -= timedelta(days=28); self.refresh_view()
    def next_month(self): self.view_date += timedelta(days=28); self.refresh_view()

if __name__ == "__main__":
    import os
    PORT = int(os.environ.get("PORT", 8080))
    print("")
    print("=" * 50)
    print("  Family Calendar Web - Server starting")
    print("  Open in browser: http://127.0.0.1:%s" % PORT)
    print("  Or: http://localhost:%s" % PORT)
    print("=" * 50)
    print("")
    app.run(host="0.0.0.0", port=PORT, debug=True)