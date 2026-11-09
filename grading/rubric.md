# 2회차 실습 평가표

`README.md`의 기초 실습(기능 네 개)과 심화 실습(배포)을 제대로 마쳤는지 확인합니다.
채점하는 사람도, 실습하는 사람도 같은 표를 봅니다 — 실습을 마친 뒤 스스로 점검하는 데 써도 됩니다.

- **한 사람 = Repository 하나**로 채점합니다. Pair에게 해 준 Review(W4)는 Pair의 Repository에서 찾습니다.
- 근거는 네 가지입니다.
  - **GitHub 기록** — Issue · Pull Request · Review · Commit
  - **코드** — `main`의 `main.py`를 이 컴퓨터에서 임시 SQLite로 실행해 API 계약을 시험하고, `index.html`의 함수 네 개를 읽는다
  - **배포한 서비스** — Render API와 Cloudflare Pages 화면에 실제로 접속한다 (GET · OPTIONS만 — 학생의 DB에 쓰지 않는다)
  - **학생 확인** — 공개된 곳에서 볼 수 없는 것(어느 DB를 쓰는가)
- 자동으로 판정할 수 있는 것은 `grading/collect.py`가 판정하고, 코드 · 의견의 **내용**은 AI나 사람이 아래 기준으로 봅니다.

## 점수 매기는 법

| 판정 | 점수 |
|---|---|
| 충족 | 배점 전부 |
| 부분 | 배점의 절반 (홀수는 올림) — T1 · T2는 통과한 비율만큼 |
| 미충족 | 0점 |
| 사람 확인 | 일단 0점. 채점자가 확인하면 충족 · 부분 · 미충족으로 바꾼다 |

**최종 판정**

| 판정 | 조건 | 다음 할 일 |
|---|---|---|
| 완료 | 70점 이상이고 «미충족» 항목이 없다 («사람 확인»은 미충족이 아니다) | 남은 «사람 확인»만 마무리 |
| 보완 | 그 밖의 경우 | «미충족» · «부분» 항목의 근거를 보고 그 단계만 다시 해 온다 |

## 평가 항목 — 합계 100점

### 기초 실습 (60점)

| # | 항목 | 배점 | 충족 | 부분 | 미충족 | 어디서 보나 |
|---|---|---|---|---|---|---|
| W1 | 기능 PR 흐름 | 15 | `main.py`를 고친 PR이 **세 개 이상**(②③을 묶으면 셋) 합쳐졌고, 모두 Issue 연결(`Closes #번호`) · Branch `feat/#번호-설명` · 제목 `[#번호] 내용` · Squash and merge · Issue 자동 닫힘 | 합친 PR이 있지만 규칙을 어긴 곳이 있거나 세 개보다 적다 | 합친 기능 PR이 없다 | Pull requests 탭 |
| W2 | Commit 규칙 | 5 | 기능 PR의 본인 Commit이 모두 `#번호 type: 내용` | 위반이 절반 이하 | 위반이 절반을 넘는다 | 각 PR의 Commits 탭 |
| W3 | Review 받기 | 10 | 모든 기능 PR이 **합치기 전에** Pair의 Approve를 받았다 | 일부만 | 하나도 없다 | 각 PR의 Reviewers |
| W4 | Pair Review 해 주기 | 5 | Pair의 기능 PR 가운데 4분의 3 이상에 Review를 남겼다 **(AI 확인)** | 일부만 | Pair의 PR에 Review가 없다 | Pair의 Repository |
| T1 | API 동작 | 15 | 아래 **자동 테스트 8개**를 모두 통과 | 통과한 비율만큼 (8개 중 5개면 15 × 5/8 ≈ 9점) | 하나도 통과하지 못했거나 서버가 뜨지 않는다 | `main.py` |
| T2 | 화면 fetch 함수 | 10 | `createTodo` · `updateTitle` · `setCompleted` · `deleteTodo` 넷 다 알맞은 Method로 `fetch`를 부른다 **(AI 확인)** | 채운 비율만큼 (함수 하나에 2.5점) | 넷 다 비어 있다 | `index.html` |

**T1 자동 테스트 8개** (README의 API 계약 그대로)

1. 등록 — `POST /todos {"title": "  공부하기 "}` → `201`, 제목은 앞뒤 공백을 지운 `공부하기`, `completed: false`
2. 빈 제목 — `POST /todos {"title": "   "}` → `400`
3. 목록 — `GET /todos`가 최신순
4. 제목 수정 — `PATCH /todos/{id} {"title": …}` → `200`, 제목이 바뀜
5. 완료 변경 — `PATCH /todos/{id} {"completed": true}` → `200`, 제목은 그대로이고 다시 조회해도 저장되어 있다
6. 없는 id 수정 → `404`
7. 삭제 — `DELETE /todos/{id}` → `204`, 목록에서 사라짐
8. 없는 id 삭제 → `404`

**T2에서 함수마다 들어 있어야 할 것** — `createTodo`: `fetch` · `POST` · `Content-Type` · `JSON.stringify` / `updateTitle`: `PATCH` · 본문에 `title` / `setCompleted`: `PATCH` · 본문에 `completed` / `deleteTodo`: `DELETE`

### 심화 실습 — 배포 (40점)

| # | 항목 | 배점 | 충족 | 부분 | 미충족 | 어디서 보나 |
|---|---|---|---|---|---|---|
| D1 | Render API 배포 | 10 | `main`의 `index.html`에 적힌 `API_BASE`(Render 주소)로 `GET /todos`를 보내면 `200`과 TODO 배열이 온다 | `200`이지만 배열이 아니다 | `API_BASE`가 아직 `localhost`이거나 서버가 응답하지 않는다 | `index.html`의 `API_BASE` |
| D2 | Cloudflare Pages 화면 배포 | 5 | Pages 주소가 TODO 화면을 내려주고, 그 화면의 `API_BASE`가 `main`과 같다 | 화면은 뜨지만 `API_BASE`가 다르다(다시 배포 안 됨) 또는 다른 페이지가 뜬다 | 주소가 응답하지 않는다 | Pages 주소 |
| D3 | CORS | 10 | Pages 주소를 `Origin`으로 보내면 API가 그 주소를 허락한다 (일반 요청 · 사전 요청 둘 다) | `*`로 아무 주소나 허락했다 | 허락하지 않는다 | API 응답의 `Access-Control-Allow-Origin` |
| D4 | PostgreSQL 전환 | 5 | **(사람 확인)** 학생이 Supabase Table Editor에서, Pages 화면으로 등록한 TODO가 보이는 것을 보여 준다 | — | 보여 주지 못한다 | 학생 화면 · 캡처 |
| D5 | 비밀 값 관리 | 10 | 모든 Branch의 Commit 이력 어디에도 비밀번호가 든 DB 주소가 없다 | 이력에 `todo.db`나 `.env` 파일이 있다 | **이력에 DB 비밀번호가 있다** — 파일을 지웠어도 이력에 남으므로 Supabase 비밀번호를 바로 바꾸게 한다 | 저장소 전체 이력 |

Pages 주소는 채점 목록에 `pages=주소`로 적어 줍니다. 없으면 Repository의 **Website** 칸이나 Deployments에서 찾고, 그래도 없으면 D2 · D3는 «사람 확인»이 됩니다.

### 감점

| 항목 | 감점 | 기준 |
|---|---|---|
| `main` 직접 Push | −10 | PR 없이 `main`에 들어간 Commit이 있다 (Repository를 만들 때 생긴 첫 Commit은 제외). 배포 준비(`API_BASE` 바꾸기)도 PR로 한다 |

## AI 확인 항목의 기준

자동 판정은 «있는가»만 봅니다. 아래 항목은 **내용**을 읽고 판정을 **내릴 수만** 있습니다 — 자동 판정이 «미충족»인 것을 올리지는 않습니다.

**T2 화면 fetch 함수** — 함수 본문을 읽는다.

- 함수 하나를 «안 됨»으로 돌릴 때: 주소가 틀렸다(`/todo`, id를 끼우지 않음), 다른 함수의 Method를 썼다(`setCompleted`가 `title`을 보냄), `await`나 `return check(res, …)`가 없어 오류가 화면에 나오지 않는다.
- 들여쓰기 · 따옴표 모양 · 변수 이름은 보지 않는다.

**W4 Pair Review 해 주기**

- 충족을 유지: Approve만 눌렀어도 된다 — 2회차는 «Pair가 확인했다»가 목적이다.
- 부분으로 내림: Review가 전부 학생 자신이 합친 **뒤에** 달렸다(합치기 전 확인이 아니다).

## 채점할 때 지킬 것

- **T1은 학생의 코드를 내 컴퓨터에서 실행한다.** 임시 폴더 · 임시 SQLite에서 돌지만, 처음 보는 Repository면 `main.py`를 먼저 훑어보거나 `--no-run`으로 건너뛴다.
- **비밀 값을 옮겨 적지 않는다.** 스크립트는 비밀번호를 `****`로 가린다. D5가 «미충족»이면 학생에게 바로 알리고 Supabase에서 **Database password를 바꾸게** 한다.
- 채점 결과는 **이 Repository에 Commit하지 않는다.** 개인별 점수는 Repository 밖에 둔다.
- 배포한 서비스에는 **읽기 요청만** 보낸다. 등록 · 삭제를 시험하고 싶으면 학생이 보는 앞에서 화면으로 한다.
- 학생의 Repository에 Comment · Review를 남기는 것은 채점자가 직접 결정한다. 채점 도구는 GitHub에 아무것도 쓰지 않는다.
