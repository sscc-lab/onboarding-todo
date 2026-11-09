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
    """TODO 등록."""
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="제목을 입력하세요")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO todo (title, completed, created_at) VALUES (?, 0, ?)",
            (title, now()),
        )
        row = conn.execute("SELECT * FROM todo WHERE id = ?", (cur.lastrowid,)).fetchone()
    return to_dict(row)


@app.patch("/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    """TODO 수정 · 완료 변경."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="없는 TODO입니다")
        if body.title is not None:
            title = body.title.strip()
            if not title:
                raise HTTPException(status_code=400, detail="제목을 입력하세요")
            conn.execute("UPDATE todo SET title = ? WHERE id = ?", (title, todo_id))
        if body.completed is not None:
            conn.execute("UPDATE todo SET completed = ? WHERE id = ?", (int(body.completed), todo_id))
        row = conn.execute("SELECT * FROM todo WHERE id = ?", (todo_id,)).fetchone()
    return to_dict(row)


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """TODO 삭제."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM todo WHERE id = ?", (todo_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="없는 TODO입니다")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")
