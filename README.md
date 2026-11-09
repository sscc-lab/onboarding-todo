# onboarding-todo

SSCCOps Maintainer Onboarding **2회차 · Web Fundamentals** 실습용 Repository입니다.

브라우저에서 버튼을 누르면 데이터가 어디를 거쳐 저장되는지, 작은 TODO 서비스를 직접 완성하고 인터넷에 배포하면서 확인합니다.

```text
Browser ─HTTP─▶ FastAPI ─▶ SQLAlchemy(ORM) ─SQL─▶ Database
(index.html)    (main.py)                         (SQLite → PostgreSQL)
localhost:5500  localhost:8000
```

화면(`index.html`)과 API(`main.py`)는 **처음부터 서로 다른 서버**에서 돕니다. 배포할 때 화면은 Cloudflare Pages, API는 Render로 가는데, 로컬에서도 같은 모양으로 연습합니다.

## 파일 구성

| 파일 | 하는 일 |
|---|---|
| `index.html` | 화면. 버튼을 누르면 `fetch`로 `API_BASE`(기본 `http://localhost:8000`)의 API를 부른다 — **완성되어 있다** |
| `main.py` | API 서버. `/todos` API를 처리한다 — **조회만 완성, 나머지는 실습에서 구현** |
| `requirements.txt` | 서버가 쓰는 Python 패키지 목록 (FastAPI · SQLAlchemy · PostgreSQL 드라이버) |
| `todo.db` | 처음 실행하면 생기는 SQLite 파일. Git에 올리지 않는다(`.gitignore`) |

> 일부러 `main.py` 한 파일에 설정 · DB 모델 · HTTP 처리 · 검증을 모두 넣었습니다.
> 기능을 넣을수록 파일이 어떻게 복잡해지는지 느껴 보세요. 그 불편함이 3회차의 출발점입니다.

## SQLAlchemy(ORM)를 쓰는 이유

데이터베이스는 SQL로 다룹니다. 그런데 SQLite와 PostgreSQL은 SQL 문법이 조금씩 달라서(값 자리 `?` / `%s`, 자동 증가 번호, 참 · 거짓 타입 등),
SQL을 직접 쓰면 DB를 바꿀 때 코드를 여기저기 고쳐야 합니다.

**ORM(Object-Relational Mapping)** 은 테이블을 Python 클래스로, 행을 객체로 다루게 해 주고, 실제 SQL은 DB 종류에 맞게 대신 만들어 줍니다.
그래서 이 Repository는 **`DATABASE_URL` 하나만 바꾸면** SQLite에서 PostgreSQL로 옮겨 갑니다.

```python
class Todo(Base):                       # 테이블 todo = 클래스 Todo
    __tablename__ = "todo"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    ...

session.add(Todo(title="공부하기", ...))   # → INSERT INTO todo (...) VALUES (...)
session.get(Todo, 3)                    # → SELECT ... FROM todo WHERE todo.id = 3
```

> `create_engine(..., echo=True)`로 켜 두었기 때문에, 서버 터미널에 **SQLAlchemy가 실제로 실행한 SQL**이 그대로 찍힙니다.
> 버튼을 누를 때마다 어떤 SQL이 나가는지 같이 보세요.

## API 계약

| Method | 경로 | 요청 본문 | 성공 응답 | 실패 |
|---|---|---|---|---|
| `GET` | `/todos` | — | `200` TODO 배열 (최신순) | — |
| `POST` | `/todos` | `{"title": "공부하기"}` | `201` 만든 TODO | 제목이 비면 `400` |
| `PATCH` | `/todos/{id}` | `{"title": "…"}` 또는 `{"completed": true}` | `200` 바뀐 TODO | 없는 id면 `404` |
| `DELETE` | `/todos/{id}` | — | `204` (본문 없음) | 없는 id면 `404` |

TODO 하나의 모양:

```json
{ "id": 1, "title": "공부하기", "completed": false, "created_at": "2026-11-16T19:30:00" }
```

## 0. 준비

이번 주부터는 **각자 자기 Repository**에서 작업합니다. 1회차와 같은 흐름(Issue → Branch → PR → Review → Squash Merge)을 그대로 쓰고, Review는 Pair에게 받습니다.

1. 이 페이지 오른쪽 위의 **Use this template → Create a new repository** → Owner는 **내 계정**, 이름은 `onboarding-todo`, Public.
2. 내 Repository의 **Settings → Collaborators**에서 Pair를 초대합니다(Review를 받기 위해).
3. 내려받고 실행합니다. Python 3.10 이상이 필요합니다.

```bash
git clone https://github.com/<내 GitHub 아이디>/onboarding-todo.git
cd onboarding-todo

python -m venv .venv
source .venv/bin/activate        # Windows(Git Bash): source .venv/Scripts/activate
pip install -r requirements.txt
```

4. **터미널 두 개**를 엽니다. 하나는 API, 하나는 화면입니다.

   ```bash
   # 터미널 ① — API 서버
   uvicorn main:app --reload               # → http://localhost:8000

   # 터미널 ② — 화면 (같은 폴더에서)
   python -m http.server 5500              # → http://localhost:5500
   ```

   > VS Code의 **Live Server** 확장을 써도 됩니다. 기본 주소가 같은 `http://localhost:5500`입니다.

5. 브라우저에서 **http://localhost:5500** 을 엽니다. 목록은 비어 있고, **등록 버튼을 누르면 `501` 오류**가 보이면 정상입니다 — 아직 구현하지 않았으니까요.
6. **http://localhost:8000/docs** 를 열면 FastAPI가 만들어 준 API 문서에서 요청을 직접 보내 볼 수 있습니다.

> 브라우저 **개발자 도구(F12) → Network 탭**을 켜 두세요. 버튼을 누를 때마다 어떤 Request가 나가고 어떤 Response가 오는지 보입니다.

> `index.html`을 파일 탐색기에서 더블클릭해 열면(`file://`) 화면의 주소가 없어서 CORS로 막힙니다. 꼭 5500번 서버로 엽니다.

### 왜 CORS 설정이 처음부터 들어 있나

화면(`localhost:5500`)과 API(`localhost:8000`)는 **포트가 달라서 서로 다른 출처(origin)** 입니다.
브라우저는 다른 출처의 API를 부를 때, **API 서버가 «이 화면 주소는 허락한다»고 응답에 적어 줘야만** 결과를 화면에 넘깁니다. 이것이 CORS입니다.
그래서 `main.py`에는 로컬 화면 주소(`http://localhost:5500`, `http://127.0.0.1:5500`)를 허락하는 설정이 미리 들어 있습니다.
배포하면 화면 주소가 Cloudflare Pages로 바뀌므로, 그 주소를 환경변수 `ALLOWED_ORIGINS`로 넘깁니다(2-5).

## 1. 기초 실습 — 기능 네 개 완성하기

기능마다 **Issue 하나 · Branch 하나 · PR 하나**로 진행합니다. `main.py`의 각 함수 주석에 할 일이 적혀 있습니다.

| 순서 | Issue 제목 | Branch | 함수 |
|---|---|---|---|
| ① | TODO 등록 | `feat/#1-create` | `create_todo` |
| ② | TODO 제목 수정 | `feat/#2-update-title` | `update_todo` (title) |
| ③ | TODO 완료 · 미완료 변경 | `feat/#3-toggle` | `update_todo` (completed) |
| ④ | TODO 삭제 | `feat/#4-delete` | `delete_todo` |

> 번호는 화면에서 받은 내 Issue 번호로 바꿔 쓰세요.

한 기능의 흐름 (등록 예):

```bash
git switch main && git pull
git switch -c feat/#1-create

# main.py의 create_todo를 구현하고, 브라우저에서 등록이 되는지 확인한다
git add main.py
git commit -m "#1 feat: TODO 등록 API 구현"
git push -u origin feat/#1-create
# → PR [#1] TODO 등록 (본문에 Closes #1) → Pair에게 Review → Squash and merge
```

**구현 힌트**

```python
# 등록 — 객체를 만들어 session에 넣고 commit하면 INSERT가 실행된다
with Session(engine) as session:
    todo = Todo(title=title, completed=False, created_at=now())
    session.add(todo)
    session.commit()
    session.refresh(todo)        # DB가 정한 id를 받아 온다
    return to_dict(todo)

# 수정 · 삭제 — 없는 id면 404
todo = session.get(Todo, todo_id)
if todo is None:
    raise HTTPException(status_code=404, detail="없는 TODO입니다")
todo.completed = True            # 속성을 바꾸고 commit하면 UPDATE
session.delete(todo)             # delete 뒤 commit하면 DELETE
session.commit()
```

**확인할 것** — 버튼을 누를 때 Network 탭에서:

- 어떤 **Method**와 **URL**로 요청이 나가는가
- 요청 본문(**Payload**)은 어떤 JSON인가
- 응답 **Status Code**와 본문은 무엇인가
- 서버를 껐다 켜도 TODO가 남아 있는가 — 왜 그런가(`todo.db`)
- 서버 터미널에는 어떤 SQL이 찍혔는가 (`INSERT` · `UPDATE` · `DELETE`)

## 2. 심화 실습 — 인터넷에 배포하기

로컬에서 한 대가 하던 일을 세 서비스로 나눕니다. 모두 **본인 계정으로 가입**하고 무료 플랜으로 진행합니다.

```text
Browser ─▶ Cloudflare Pages (index.html)
              │ HTTPS / JSON
              ▼
           Render (FastAPI · main.py)
              │ SQL
              ▼
           Supabase (PostgreSQL)
```

이번 단계도 Issue · Branch · PR로 나눠 진행합니다.

### 2-1. Supabase — PostgreSQL 만들기

1. Supabase에서 새 Project를 만들고, 데이터베이스 비밀번호를 정해 **따로 적어 둡니다**.
2. Project의 **Connect** 버튼에서 연결 문자열(Connection string)을 복사합니다.
   `[YOUR-PASSWORD]` 자리에 비밀번호를 넣습니다. 이 문자열이 `DATABASE_URL`입니다.

> 이 값은 비밀번호가 들어 있으므로 **절대 커밋하지 않습니다.** 서비스의 환경변수에만 넣습니다.
> Render처럼 IPv4로 접속하는 곳에서는 Direct connection이 안 될 수 있습니다. 그때는 같은 화면의 **Session pooler** 연결 문자열을 씁니다.

### 2-2. PostgreSQL로 바꾸기 — 코드는 그대로, `DATABASE_URL`만

`main.py`는 `DATABASE_URL` 환경변수가 있으면 그 DB를, 없으면 `todo.db`(SQLite)를 씁니다. 코드는 고치지 않습니다.

```bash
export DATABASE_URL="postgresql://postgres:…@…"     # 2-1에서 복사한 주소 (Windows Git Bash도 같다)
uvicorn main:app --reload
```

서버가 뜨면 SQLAlchemy가 Supabase에 `todo` 테이블을 만들고, 터미널에 찍히는 SQL이 PostgreSQL용으로 바뀝니다.
Supabase 대시보드의 **Table Editor**에서 브라우저로 등록한 TODO가 보이면 성공입니다.

| | SQLite | PostgreSQL | 누가 맞춰 주나 |
|---|---|---|---|
| 위치 | 내 컴퓨터의 파일 | 인터넷 너머의 서버 | `DATABASE_URL` |
| 값 자리 | `?` | `%s` | SQLAlchemy |
| 자동 증가 번호 | `AUTOINCREMENT` | `SERIAL` · `IDENTITY` | SQLAlchemy |
| 참 · 거짓 | `0` / `1` | `TRUE` / `FALSE` | SQLAlchemy |
| 드라이버 | Python에 들어 있음 | `psycopg` (requirements.txt) | `main.py`가 주소를 `postgresql+psycopg://`로 맞춘다 |

> `export`한 값은 그 터미널에만 있습니다. 파일에 적어 커밋하지 않습니다.

### 2-3. Render — Backend 배포

1. Render에서 **New → Web Service** → 내 `onboarding-todo` Repository 연결.
2. 설정:
   - Runtime: **Python**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: **Free**
3. **Environment**에 `DATABASE_URL`을 넣습니다.
4. 배포가 끝나면 `https://<서비스 이름>.onrender.com/todos` 를 열어 `[]`이 보이는지 확인합니다.

> 무료 인스턴스는 한동안 요청이 없으면 잠들고, 다음 요청에서 깨어나느라 첫 응답이 느립니다.

### 2-4. Cloudflare Pages — Frontend 배포

1. `index.html`의 `API_BASE`를 Render 주소로 바꿔 커밋합니다.

   ```js
   const API_BASE = "https://<서비스 이름>.onrender.com";
   ```

2. Cloudflare에서 **Pages → Connect to Git** → 내 Repository → Framework preset **None**, Build command는 비우고, Build output directory는 `/`.
3. 배포가 끝나면 `https://<프로젝트 이름>.pages.dev` 를 엽니다.

### 2-5. CORS — 배포한 화면 주소를 허락하기

Pages 화면에서 등록을 누르면 아마 실패하고, 개발자 도구 Console에 **CORS** 오류가 보일 겁니다.
API가 허락한 주소는 아직 로컬 화면(`localhost:5500`)뿐이고, 새 화면 주소(`pages.dev`)는 모르기 때문입니다.

Render의 **Environment**에 화면 주소를 넣고 다시 배포합니다. 쉼표로 여러 개를 적을 수 있습니다.

```text
ALLOWED_ORIGINS=https://<프로젝트 이름>.pages.dev,http://localhost:5500
```

> `allow_origins=["*"]`로 아무 주소나 허락하면 오류는 사라지지만, 다른 사이트도 이 API를 마음대로 부를 수 있게 됩니다. 쓰지 않습니다.

### 2-6. 확인할 흐름

등록 버튼 하나가 지나가는 길을 자기 말로 설명할 수 있으면 완료입니다.

```text
Browser → Cloudflare Pages(index.html) → HTTP Request → Render(FastAPI) → Supabase(PostgreSQL)
        → FastAPI → HTTP Response → Browser
```

## 막힐 때

| 보이는 것 | 의심할 곳 |
|---|---|
| `501 아직 구현하지 않았습니다` | 그 함수를 아직 구현하지 않았다 |
| `422 Unprocessable Entity` | 요청 본문의 JSON 모양이 API 계약과 다르다 |
| `404 Not Found` | 경로(URL) 오타, 또는 없는 id |
| `500 Internal Server Error` | 서버 코드의 예외 — `uvicorn` 터미널(또는 Render Logs)의 오류를 읽는다 |
| `Failed to fetch` · CORS 오류 | API 서버가 켜져 있는가, `API_BASE` 주소, `ALLOWED_ORIGINS`에 지금 화면 주소가 있는가, `file://`로 열지 않았는가 |
| `[Errno 13]` · `10013` 포트 바인딩 실패 (Windows) | 그 포트를 Windows가 예약해 두었다 — `uvicorn main:app --reload --port 9000`처럼 바꾸고 `API_BASE`도 같이 바꾼다 |
| Render 배포 실패 | Render의 Logs에서 Build 단계인지 Start 단계인지부터 본다 |
| DB 연결 실패 | `DATABASE_URL` 비밀번호 · 주소, 또는 Session pooler 주소 사용 여부 |
| `ModuleNotFoundError: psycopg` | `pip install -r requirements.txt`를 다시 실행 |

## 완료 체크리스트

- [ ] 기능 네 개를 Issue · Branch · PR로 하나씩 완성했다
- [ ] Network 탭에서 Method · URL · Status Code · 본문을 확인했다
- [ ] `DATABASE_URL`만으로 SQLite에서 PostgreSQL로 옮기고, 비밀 값은 환경변수에만 넣었다
- [ ] Render · Cloudflare Pages에 배포해 실제 URL로 TODO를 등록했다
- [ ] 화면과 API의 주소가 다를 때 CORS가 왜 필요한지 설명하고, 배포 주소를 허락했다
- [ ] 버튼 하나가 지나가는 길을 자기 말로 설명할 수 있다

## 규칙

1회차와 같습니다 — Branch `feat/#번호-설명`, Commit `#번호 type: 내용`, PR `[#번호] 내용`, Squash and merge, `main`에 직접 Push하지 않기.
