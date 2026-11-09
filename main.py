"""TODO 서버 — 2회차 실습용.

일부러 파일 하나에 모든 것을 넣었습니다(HTTP 처리 · 검증 · SQL · 설정).
기능이 늘수록 이 파일이 얼마나 복잡해지는지 느껴 보는 것이 이번 주의 목적이고,
그 불편함이 3회차(Layered Architecture)의 출발점입니다.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "todo.db"

app = FastAPI(title="onboarding-todo")


# ── Database ──────────────────────────────────────────────


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 결과를 dict처럼 꺼낼 수 있게
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todo (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                completed  INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL
            )
            """
        )


init_db()


def to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": bool(row["completed"]),
        "created_at": row["created_at"],
    }


# ── 요청 본문 모양 ─────────────────────────────────────────


class TodoCreate(BaseModel):
    title: str


class TodoUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None


# ── 화면 ──────────────────────────────────────────────────


@app.get("/")
def index():
    # 로컬에서는 FastAPI가 화면(index.html)도 함께 내려줍니다.
    return FileResponse(Path(__file__).parent / "index.html")


# ── API ───────────────────────────────────────────────────


@app.get("/todos")
def list_todos():
    """TODO 목록 조회 — 예시로 완성해 둔 API입니다."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM todo ORDER BY id DESC").fetchall()
    return [to_dict(r) for r in rows]


@app.post("/todos", status_code=201)
def create_todo(body: TodoCreate):
    """TODO 등록 — 실습 ①에서 구현합니다.

    1. body.title이 비어 있으면 400을 돌려준다 (HTTPException)
    2. INSERT INTO todo (title, completed, created_at) VALUES (?, 0, ?)
    3. 방금 만든 행을 다시 SELECT해서 dict로 돌려준다 (cursor.lastrowid)
    """
    raise HTTPException(status_code=501, detail="아직 구현하지 않았습니다")


@app.patch("/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    """TODO 수정 · 완료 변경 — 실습 ②③에서 구현합니다.

    1. 해당 id가 없으면 404
    2. body.title이 있으면 title을, body.completed가 있으면 completed를 UPDATE
    3. 바뀐 행을 dict로 돌려준다
    """
    raise HTTPException(status_code=501, detail="아직 구현하지 않았습니다")


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """TODO 삭제 — 실습 ④에서 구현합니다.

    1. 해당 id가 없으면 404
    2. DELETE FROM todo WHERE id = ?
    """
    raise HTTPException(status_code=501, detail="아직 구현하지 않았습니다")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
