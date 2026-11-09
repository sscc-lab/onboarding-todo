#!/usr/bin/env python3
"""학생의 main.py를 임시 SQLite로 띄워 README의 API 계약대로 동작하는지 본다.

collect.py가 별도 프로세스로 부른다 (python grading/api_test.py <main.py가 있는 폴더> <결과 JSON 경로>).
DATABASE_URL은 collect.py가 임시 SQLite 파일로 덮어써서 넘긴다 — 학생의 실제 DB에는 닿지 않는다.
"""
import importlib.util
import json
import os
import sys
import traceback


def main():
    src, out = sys.argv[1], sys.argv[2]
    results = []

    def record(name, fn):
        try:
            fn()
            results.append({"name": name, "ok": True, "detail": ""})
        except AssertionError as e:
            results.append({"name": name, "ok": False, "detail": str(e)[:300]})
        except Exception as e:  # 학생 코드의 예외도 실패로 남긴다
            results.append({"name": name, "ok": False, "detail": f"{type(e).__name__}: {e}"[:300]})

    try:
        sys.path.insert(0, src)
        spec = importlib.util.spec_from_file_location("student_main", os.path.join(src, "main.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from fastapi.testclient import TestClient
        c = TestClient(mod.app, raise_server_exceptions=False)
    except Exception:
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"load_error": traceback.format_exc()[-800:], "results": []}, f, ensure_ascii=False)
        return

    state = {}

    def create():
        r = c.post("/todos", json={"title": "  공부하기 "})
        assert r.status_code == 201, f"상태 코드 {r.status_code} (201이어야 함) {r.text[:120]}"
        t = r.json()
        assert t.get("title") == "공부하기", f"제목 {t.get('title')!r} — 앞뒤 공백을 지워야 함"
        assert t.get("completed") is False, "completed가 false가 아님"
        assert isinstance(t.get("id"), int), "id가 없음"
        state["id"] = t["id"]

    def blank():
        r = c.post("/todos", json={"title": "   "})
        assert r.status_code == 400, f"상태 코드 {r.status_code} (400이어야 함)"

    def order():
        r = c.post("/todos", json={"title": "둘째"})
        assert r.status_code == 201, f"두 번째 등록 상태 코드 {r.status_code}"
        state["id2"] = r.json()["id"]
        titles = [x["title"] for x in c.get("/todos").json()]
        assert titles[:2] == ["둘째", "공부하기"], f"목록 {titles} — 최신순이어야 함"

    def patch_title():
        r = c.patch(f"/todos/{state['id']}", json={"title": "복습하기"})
        assert r.status_code == 200, f"상태 코드 {r.status_code} (200이어야 함)"
        assert r.json().get("title") == "복습하기", "제목이 바뀌지 않음"

    def patch_done():
        r = c.patch(f"/todos/{state['id']}", json={"completed": True})
        assert r.status_code == 200, f"상태 코드 {r.status_code} (200이어야 함)"
        t = r.json()
        assert t.get("completed") is True, "completed가 true로 바뀌지 않음"
        assert t.get("title") == "복습하기", "완료만 바꿨는데 제목이 달라짐"
        again = [x for x in c.get("/todos").json() if x["id"] == state["id"]]
        assert again and again[0]["completed"] is True, "다시 조회하면 저장되어 있지 않음 (commit 확인)"

    def patch_404():
        r = c.patch("/todos/99999", json={"completed": True})
        assert r.status_code == 404, f"상태 코드 {r.status_code} (404여야 함)"

    def delete():
        r = c.delete(f"/todos/{state['id']}")
        assert r.status_code == 204, f"상태 코드 {r.status_code} (204여야 함)"
        ids = [x["id"] for x in c.get("/todos").json()]
        assert state["id"] not in ids, "삭제했는데 목록에 남아 있음"

    def delete_404():
        r = c.delete("/todos/99999")
        assert r.status_code == 404, f"상태 코드 {r.status_code} (404여야 함)"

    for name, fn in [
        ("등록 — POST /todos → 201, 공백을 지운 제목", create),
        ("빈 제목 — POST /todos → 400", blank),
        ("목록 — GET /todos 최신순", order),
        ("제목 수정 — PATCH → 200", patch_title),
        ("완료 변경 — PATCH → 200, 저장됨", patch_done),
        ("없는 id 수정 — PATCH → 404", patch_404),
        ("삭제 — DELETE → 204, 목록에서 사라짐", delete),
        ("없는 id 삭제 — DELETE → 404", delete_404),
    ]:
        record(name, fn)

    with open(out, "w", encoding="utf-8") as f:
        json.dump({"load_error": None, "results": results}, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
