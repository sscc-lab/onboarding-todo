"""TODO 서버 — 2회차 실습용.

일부러 파일 하나에 모든 것을 넣었습니다(설정 · DB 모델 · HTTP 처리 · 검증).
기능이 늘수록 이 파일이 얼마나 복잡해지는지 느껴 보는 것이 이번 주의 목적이고,
그 불편함이 3회차(Layered Architecture)의 출발점입니다.
"""

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# ── 설정 ──────────────────────────────────────────────────
# DB 주소는 코드가 아니라 환경변수 DATABASE_URL에서 읽습니다.
# 없으면 이 폴더의 todo.db(SQLite)를 씁니다. 심화 실습에서 Supabase 주소를 넣으면 PostgreSQL이 됩니다.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'todo.db'}")
# Supabase가 주는 postgresql:// 주소를 psycopg(3) 드라이버로 연결하도록 맞춥니다.
if DATABASE_URL.startswith(("postgresql://", "postgres://")):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.split("://", 1)[1]

# echo=True — SQLAlchemy가 실제로 실행하는 SQL을 터미널에 보여 줍니다.
engine = create_engine(DATABASE_URL, echo=True)

app = FastAPI(title="onboarding-todo")


# ── DB 모델 — 테이블 하나 = 클래스 하나 ─────────────────────


class Base(DeclarativeBase):
    pass


class Todo(Base):
    __tablename__ = "todo"

    id: Mapped[int] = mapped_column(primary_key=True)  # 자동 증가 번호
    title: Mapped[str] = mapped_column(String(200))
    completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(32))


Base.metadata.create_all(engine)  # 테이블이 없으면 만든다


def to_dict(todo: Todo) -> dict:
    return {
        "id": todo.id,
        "title": todo.title,
        "completed": todo.completed,
        "created_at": todo.created_at,
    }


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


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
    with Session(engine) as session:
        todos = session.scalars(select(Todo).order_by(Todo.id.desc())).all()
        return [to_dict(t) for t in todos]


@app.post("/todos", status_code=201)
def create_todo(body: TodoCreate):
    """TODO 등록 — 실습 ①에서 구현합니다.

    1. body.title의 앞뒤 공백을 지우고, 비어 있으면 400을 돌려준다 (HTTPException)
    2. Todo(title=..., completed=False, created_at=now())를 만들어 session.add
    3. session.commit()으로 저장하고, session.refresh로 새 id를 받아 dict로 돌려준다
    """
    raise HTTPException(status_code=501, detail="아직 구현하지 않았습니다")


@app.patch("/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    """TODO 수정 · 완료 변경 — 실습 ②③에서 구현합니다.

    1. session.get(Todo, todo_id)로 찾고, 없으면 404
    2. body.title이 있으면 title을, body.completed가 있으면 completed를 바꾼다
    3. session.commit() 뒤 dict로 돌려준다
    """
    raise HTTPException(status_code=501, detail="아직 구현하지 않았습니다")


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """TODO 삭제 — 실습 ④에서 구현합니다.

    1. session.get(Todo, todo_id)로 찾고, 없으면 404
    2. session.delete(todo) 뒤 session.commit()
    """
    raise HTTPException(status_code=501, detail="아직 구현하지 않았습니다")
