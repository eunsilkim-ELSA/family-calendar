# 가족 일정표 — DB 버전 적용 가이드

Render에 배포한 일정표에서 **일정이 서버 재시작 후에도 유지**되려면 **PostgreSQL** DB를 연결하면 됩니다.

---

## 1. 전체 순서 요약

| 순서 | 할 일 |
|------|--------|
| ① | **Render**에서 **PostgreSQL** 데이터베이스 생성 |
| ② | 웹 서비스에 **DATABASE_URL** 환경 변수로 DB 연결 |
| ③ | PC에서 **family_app.py**를 DB 버전으로 교체 |
| ④ | **requirements.txt**에 DB 라이브러리 추가 |
| ⑤ | **GitHub**에 푸시 → Render 자동 재배포 |

---

## 2. Render에서 PostgreSQL 만들기

1. **Render** (https://render.com) 로그인 → **Dashboard**
2. **New +** 클릭 → **PostgreSQL** 선택
3. 설정 입력:
   - **Name:** `family-calendar-db` (원하는 이름)
   - **Region:** 웹 서비스와 **같은 지역** (예: Singapore)
   - **Plan:** **Free**
4. **Create Database** 클릭
5. 생성이 끝나면 DB 화면에서 **Internal Database URL** 확인 (나중에 연결할 때 사용)

---

## 3. 웹 서비스에 DB 연결하기

**방법 A — 자동 연결 (권장)**

1. **Dashboard** → 방금 만든 **PostgreSQL** 서비스 클릭
2. 오른쪽 **Connect** 섹션에서 **family-calendar** (웹 서비스 이름) 선택
3. **Connect** 클릭  
   → 웹 서비스에 **DATABASE_URL**이 자동으로 설정됨

**방법 B — 수동 입력**

1. **Dashboard** → **family-calendar** (웹 서비스) 클릭
2. **Environment** 탭 → **Add Environment Variable**
3. **Key:** `DATABASE_URL`
4. **Value:** PostgreSQL 서비스의 **Internal Database URL** 붙여넣기
5. **Save Changes**

---

## 4. PC에서 파일 수정 (D:\Coding practice)

### 4-1. family_app.py를 DB 버전으로 교체

1. **문서** 폴더에서 **family_app_DB버전.py** 파일을 연다.
2. **전체 선택 (Ctrl+A)** → **복사 (Ctrl+C)**
3. **D:\Coding practice\family_app.py**를 연다.
4. **전체 선택 (Ctrl+A)** → **붙여넣기 (Ctrl+V)** → **저장**

(또는 문서 폴더의 `family_app_DB버전.py`를 복사해서 `D:\Coding practice\family_app.py`를 덮어쓰기 해도 됩니다.)

### 4-2. requirements.txt 수정

**D:\Coding practice\requirements.txt**를 열어 **아래 4줄**이 되도록 수정:

```
flask>=2.0.0
gunicorn
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

---

## 5. GitHub에 올리고 재배포

**명령 프롬프트** 또는 **PowerShell**에서:

```bat
d:
cd "D:\Coding practice"
git add family_app.py requirements.txt
git status
git commit -m "Use PostgreSQL for persistent data"
git push origin main
```

Render는 **main** 브랜치에 푸시되면 자동으로 재배포합니다.  
자동 배포가 꺼져 있다면: **Render Dashboard** → 해당 웹 서비스 → **Manual Deploy** → **Deploy latest commit**

---

## 6. 동작 방식

| 환경 | 저장 위치 |
|------|-----------|
| **Render** (DATABASE_URL 있음) | **PostgreSQL** — 재시작/잠자기 후에도 일정 유지 |
| **로컬** (DATABASE_URL 없음) | **JSON 파일** (`family_pro_data.json`) — 기존처럼 동작 |

- Render에 DB 연결 후 배포하면, 모바일/PC에서 입력·수정한 일정이 **DB에 저장**되어 **사라지지 않습니다.**

---

## 7. 문제 해결

| 증상 | 확인할 것 |
|------|------------|
| 배포 후 500 에러 | Render **Logs**에서 오류 메시지 확인. **Environment**에 `DATABASE_URL` 있는지 확인. |
| ModuleNotFoundError: sqlalchemy | `requirements.txt`에 `sqlalchemy`, `psycopg2-binary` 있는지 확인 후 **재배포**. |
| 일정이 계속 사라짐 | 웹 서비스 **Environment**에 `DATABASE_URL` 설정 여부, DB와 웹 서비스 **Region**이 같은지 확인. |

---

## 8. 정리 체크리스트

- [ ] Render에서 PostgreSQL 생성
- [ ] 웹 서비스에 DATABASE_URL 연결 (Connect 또는 수동)
- [ ] `family_app.py`를 DB 버전으로 교체
- [ ] `requirements.txt`에 sqlalchemy, psycopg2-binary 추가
- [ ] `git push origin main` 후 Render 재배포 확인

이 순서대로 하면 **DB 버전**으로 일정이 유지됩니다.
