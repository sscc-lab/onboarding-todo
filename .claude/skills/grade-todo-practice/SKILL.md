---
name: grade-todo-practice
description: SSCCOps 2회차 Web 실습(onboarding-todo)을 평가표(grading/rubric.md)로 채점한다. 학생별 Repository 주소(와 Cloudflare Pages 주소)를 받아 GitHub 기록 · API 자동 테스트 · 배포한 서비스를 확인하고, 코드 · Review 내용을 봐야 하는 항목을 판정해 사람별 점수 · 판정 · 보완할 점을 보고한다. "2회차 채점" "TODO 실습 채점" "onboarding-todo 채점" "배포 확인해 줘" 요청에 쓴다.
---

# TODO 실습 채점

평가 기준의 정본은 `grading/rubric.md`다. 이 절차는 그 표를 그대로 적용하는 방법만 정한다.
기준이 이 파일과 갈리면 `rubric.md`를 따른다.

## 시작 전 확인

1. **채점 목록** — 한 줄에 한 사람: `아이디/onboarding-todo pages=https://….pages.dev`. Pages 주소가 없으면 D2 · D3가 «사람 확인»이 되므로, 받지 못했으면 물어본다(학생이 제출한 주소).
2. `gh auth status` — 로그인되어 있어야 한다.
3. `python -c "import fastapi, sqlalchemy, httpx"` — 실패하면 `pip install -r requirements.txt`. T1이 학생 `main.py`를 실행하는 데 필요하다.
4. `grading/rubric.md`를 처음부터 끝까지 읽는다.
5. **T1은 학생 코드를 이 컴퓨터에서 실행한다**는 것을 채점자에게 한 줄로 알린다. 원하지 않으면 `--no-run`을 붙인다.

## 절차

### 1. 기록 모으기와 자동 판정

결과는 Repository 바깥(임시 폴더)에 둔다. 학생 점수를 이 Repository에 Commit하지 않는다.

```bash
python grading/collect.py --list <임시 폴더>/repos.txt --format json > <임시 폴더>/evidence.json
```

- Render 무료 인스턴스가 잠들어 있으면 첫 응답에 1분 가까이 걸린다 — 사람마다 최대 90초를 기다린다.
- Windows에서 한글이 깨지면 `PYTHONIOENCODING=utf-8`을 붙인다.
- 같은 결과로 다시 채점하려면 `--raw-out raw.json`으로 저장해 두고 `--from-json raw.json`을 쓴다.

`evidence.json`은 사람마다 `items`(항목별 `status` · `score` · `evidence`)와 `penalty` · `total` · `pending_points` · `verdict`를 담는다.

### 2. AI 확인 항목 판정

`ai_check: true`인 항목(T2 · W4)만 내용을 읽고 `rubric.md`의 «AI 확인 항목의 기준»으로 판정한다.

- **내릴 수만 있다.** «미충족»은 기록이 없다는 뜻이라 올리지 않는다.
- T2는 함수 단위로 본다. 함수 하나를 «안 됨»으로 돌리면 2.5점씩 빼서 `round(10 × 된 함수 수 / 4)`로 다시 계산한다.
- 판정을 바꿨으면 이유를 한 줄로 남기고, `total` · `verdict`를 평가표 규칙으로 다시 계산한다.

자동 판정 항목은 바꾸지 않는다. 틀려 보이면 «사람 확인»과 이유를 적는다.

### 3. 보고

맨 위에 전체 요약을 둔다.

```markdown
| 아이디 | 점수 | 판정 | 사람 확인 남음 | 보완할 점 |
|---|---|---|---|---|
| @alice | 93 | 완료 | D4 PostgreSQL | — |
| @bob | 21 | 보완 | D2 · D3 · D4 · T1 | 🚨 DB 비밀번호 즉시 변경 · API_BASE를 Render 주소로 · 기능 PR 규칙 |
```

그 아래에 사람마다 `collect.py`의 항목 표를 그대로 두고, AI가 바꾼 판정에는 «AI 판정: 이유»를 덧붙인다.
보완할 점은 학생이 **다음에 무엇을 하면 되는지**로 쓴다. 남은 «사람 확인»은 채점자가 학생에게 무엇을 물으면 되는지 적는다(예: «Supabase Table Editor 화면 보여 주기»).

## 지킬 것

- **D5가 «미충족»이면 보고 맨 위에 🚨로 따로 적는다.** 채점보다 먼저 학생이 Supabase 비밀번호를 바꿔야 한다. 비밀번호는 `****`로 가린 채로만 옮긴다.
- **GitHub에 쓰지 않는다.** Comment · Review · Issue를 남기는 것은 채점자가 정한다.
- **배포한 서비스에 쓰지 않는다.** POST · PATCH · DELETE를 보내지 않는다.
- 근거 없는 판정을 하지 않는다. `evidence`에 없는 사실로 점수를 올리지 않는다.
