#!/usr/bin/env python3
"""onboarding-todo 실습 채점 — GitHub 기록 · 코드 · 배포한 서비스를 확인해 평가표(rubric.md)의 자동 판정까지 한다.

준비: gh CLI 로그인(gh auth login), 이 Repository의 requirements.txt 설치(pip install -r requirements.txt)

사용법
    python grading/collect.py 아이디/onboarding-todo
    python grading/collect.py 아이디/onboarding-todo pages=https://내프로젝트.pages.dev
    python grading/collect.py --list repos.txt --format json > ../evidence.json

repos.txt — 한 줄에 한 사람. 저장소 뒤에 key=value를 붙일 수 있다.
    alice/onboarding-todo pages=https://alice-todo.pages.dev
    bob/onboarding-todo   pages=https://bob-todo.pages.dev api=https://bob-todo.onrender.com

    pages=  Cloudflare Pages 주소 (없으면 Repository의 Website 칸 · Deployments에서 찾는다)
    api=    Render 주소 (없으면 main의 index.html에 적힌 API_BASE)
    저장소@브랜치 로 쓰면 그 Branch의 코드를 본다 (예: sscc-lab/onboarding-todo@solution)

주의: T1은 학생의 main.py를 이 컴퓨터에서 실행한다(임시 폴더 · 임시 SQLite). 실행하지 않으려면 --no-run.
배포한 서비스에는 GET · OPTIONS 요청만 보낸다 — 학생의 DB에 아무것도 쓰지 않는다.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TYPES = "feat|fix|docs|refactor|chore|init"
RE_BRANCH = re.compile(r"^(feat|fix|docs|refactor|chore)/#(\d+)-\S+$")
RE_COMMIT = re.compile(rf"^#(\d+) ({TYPES}): \S")
RE_PR_TITLE = re.compile(r"^\[#(\d+)\] \S")
RE_PR_TITLE_TYPED = re.compile(rf"^\[#\d+\] ({TYPES})\s*:")
RE_SECRET = re.compile(r"postgres(?:ql)?(?:\+\w+)?://([^\s:/'\"]+):([^\s@'\"]+)@([^\s/'\":]+)")
RE_API_BASE = re.compile(r"""^\s*const\s+API_BASE\s*=\s*["'`]([^"'`]+)["'`]""", re.M)  # 주석 속 예시 줄은 건너뛴다

ITEMS = [
    ("W1", "기초 · 기능 PR 흐름", 15),
    ("W2", "기초 · Commit 규칙", 5),
    ("W3", "기초 · Review 받기", 10),
    ("W4", "기초 · Pair Review 해 주기", 5),
    ("T1", "기초 · API 동작 (자동 테스트)", 15),
    ("T2", "기초 · 화면 fetch 함수", 10),
    ("D1", "심화 · Render API 배포", 10),
    ("D2", "심화 · Cloudflare Pages 화면 배포", 5),
    ("D3", "심화 · CORS", 10),
    ("D4", "심화 · PostgreSQL 전환", 5),
    ("D5", "심화 · 비밀 값 관리", 10),
]
POINTS = {k: p for k, _, p in ITEMS}
TITLES = {k: t for k, t, _ in ITEMS}
DIRECT_PUSH_PENALTY = 10
PASS_SCORE = 70  # 완료 = 70점 이상이고 «미충족» 항목이 없다 («사람 확인»은 미충족이 아니다)

FUNCS = {  # index.html에서 학생이 채우는 함수 → 들어 있어야 할 것
    "createTodo": ["fetch(", "POST", "JSON.stringify", "content-type"],
    "updateTitle": ["fetch(", "PATCH", "JSON.stringify", "content-type", "title"],
    "setCompleted": ["fetch(", "PATCH", "JSON.stringify", "content-type", "completed"],
    "deleteTodo": ["fetch(", "DELETE"],
}

QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner name homepageUrl
    owner { login }
    deployments(first: 20, orderBy: {field: CREATED_AT, direction: DESC}) { nodes {
      environment latestStatus { state environmentUrl }
    } }
    defaultBranchRef { target { ... on Commit {
      history(first: 100) { nodes {
        oid messageHeadline
        author { name user { login } }
        associatedPullRequests(first: 3) { nodes { number } }
      } }
    } } }
    issues(first: 100, orderBy: {field: CREATED_AT, direction: ASC}) { nodes {
      number state author { login }
      closedByPullRequestsReferences(first: 5, includeClosedPrs: true) { nodes { number } }
    } }
    pullRequests(first: 100, orderBy: {field: CREATED_AT, direction: ASC}) { nodes {
      number title state merged mergedAt headRefName
      author { login }
      mergeCommit { messageHeadline parents(first: 3) { totalCount } }
      closingIssuesReferences(first: 5) { nodes { number } }
      files(first: 50) { nodes { path } }
      commits(first: 100) { nodes { commit {
        messageHeadline parents(first: 3) { totalCount } author { name user { login } }
      } } }
      reviews(first: 50) { nodes { state submittedAt body author { login } } }
      reviewThreads(first: 50) { nodes { comments(first: 20) { nodes { body author { login } } } } }
    } }
  }
}
"""


# ───────────────────────── 수집 ─────────────────────────

def gh_repo(full):
    owner, name = full.split("/", 1)
    res = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"owner={owner}", "-F", f"name={name}"],
                         capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        return None, res.stderr.strip()
    data = json.loads(res.stdout)
    if data.get("errors") or not (data.get("data") or {}).get("repository"):
        return None, str(data.get("errors"))
    return data["data"]["repository"], None


def parse_spec(line):
    parts = line.split()
    m = re.search(r"(?:github\.com[/:])?([\w.-]+)/([\w.-]+?)(?:\.git)?/?(?:@([\w./#-]+))?$", parts[0])
    if not m:
        raise SystemExit(f"저장소 형식을 알 수 없습니다: {parts[0]} (예: 아이디/onboarding-todo)")
    opts = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
    return {"repo": f"{m.group(1)}/{m.group(2)}", "ref": m.group(3), "pages": opts.get("pages"), "api": opts.get("api")}


def git(args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def scan_secrets(dest):
    """모든 Branch의 모든 Commit에서 비밀번호가 든 DB 주소를 찾는다. 비밀번호는 가린다."""
    log = git(["log", "--all", "-p", "--no-color", "--format=commit %H"], cwd=dest).stdout
    found, sha, path = [], None, None
    for line in log.splitlines():
        if line.startswith("commit "):
            sha = line[7:14]
        elif line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):  # 비밀 값이 들어온 Commit만 적는다
            for m in RE_SECRET.finditer(line):
                if m.group(2) in ("[YOUR-PASSWORD]", "password", "PASSWORD", "…", "..."):
                    continue
                item = f"{sha} `{path}` — postgresql://{m.group(1)}:****@{m.group(3)}"
                if item not in found:
                    found.append(item)
    names = git(["log", "--all", "--format=", "--name-only"], cwd=dest).stdout.split()
    return found, sorted({n for n in names if n in ("todo.db", ".env") or n.endswith("/.env")})


def run_api_tests(dest):
    work = tempfile.mkdtemp(prefix="todo-test-")
    try:
        shutil.copy(os.path.join(dest, "main.py"), work)
        out = os.path.join(work, "result.json")
        env = dict(os.environ)
        env["DATABASE_URL"] = "sqlite:///" + os.path.join(work, "test.db").replace("\\", "/")
        env.pop("ALLOWED_ORIGINS", None)
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "api_test.py"), work, out],
                           cwd=work, env=env, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            return {"load_error": "120초 안에 끝나지 않았다", "results": []}
        data = read(out)
        return json.loads(data) if data else {"load_error": "테스트가 결과를 남기지 못했다", "results": []}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def http(url, method="GET", headers=None, timeout=30):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "onboarding-todo-grader", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"status": r.status, "headers": {k.lower(): v for k, v in r.headers.items()}, "body": r.read(200_000).decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": {k.lower(): v for k, v in e.headers.items()}, "body": ""}
    except Exception as e:
        return {"status": None, "error": f"{type(e).__name__}: {e}"[:200], "headers": {}, "body": ""}


def origin_of(url):
    m = re.match(r"^(https?://[^/]+)", url or "")
    return m.group(1) if m else None


def collect(spec, run_tests=True):
    gh, err = gh_repo(spec["repo"])
    if gh is None:
        raise SystemExit(f"[{spec['repo']}] GitHub에서 읽지 못했습니다: {err}")
    dest = tempfile.mkdtemp(prefix="todo-repo-")
    try:
        args = ["clone", "--quiet", "--no-single-branch"] + (["--branch", spec["ref"]] if spec["ref"] else []) \
            + [f"https://github.com/{spec['repo']}.git", dest]
        res = git(args)
        if res.returncode != 0:
            raise SystemExit(f"[{spec['repo']}] clone 실패: {res.stderr.strip()}")
        index_html = read(os.path.join(dest, "index.html")) or ""
        main_py = read(os.path.join(dest, "main.py")) or ""
        secrets, risky_files = scan_secrets(dest)
        local = {"index_html": index_html, "main_py_has_star": bool(re.search(r"allow_origins\s*=\s*\[\s*[\"']\*", main_py)),
                 "secrets": secrets, "risky_files": risky_files, "api": None}
        if not main_py:
            local["api"] = {"load_error": "main.py가 없다", "results": []}
        elif RE_SECRET.search(main_py):
            local["api"] = {"load_error": "main.py에 DB 주소가 적혀 있어 실행하지 않았다 (학생 DB에 닿을 수 있음)", "results": []}
        elif run_tests:
            local["api"] = run_api_tests(dest)
    finally:
        shutil.rmtree(dest, ignore_errors=True)

    m = RE_API_BASE.search(local["index_html"])
    api_base = (spec["api"] or (m.group(1) if m else "")).rstrip("/")
    pages = spec["pages"] or ""
    if not pages and gh.get("homepageUrl"):
        pages = gh["homepageUrl"]
    if not pages:
        for d in (gh.get("deployments") or {}).get("nodes") or []:
            u = ((d.get("latestStatus") or {}).get("environmentUrl")) or ""
            if "pages.dev" in u:
                pages = u
                break
    live = {"api_base": api_base, "api_from": "api=" if spec["api"] else "index.html", "pages": pages}
    if spec["api"] or (api_base.startswith("http") and not re.search(r"//(localhost|127\.0\.0\.1)", api_base)):
        live["get"] = http(api_base + "/todos", timeout=90)  # Render 무료 인스턴스는 깨어나는 데 1분 가까이 걸린다
        try:
            live["get"]["is_list"] = isinstance(json.loads(live["get"]["body"]), list)
        except ValueError:
            live["get"]["is_list"] = False
        if pages:
            o = origin_of(pages)
            live["cors_get"] = http(api_base + "/todos", headers={"Origin": o})
            live["cors_preflight"] = http(api_base + "/todos", method="OPTIONS", headers={
                "Origin": o, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    if pages:
        live["pages_get"] = http(pages)
    for k in ("get", "cors_get", "cors_preflight", "pages_get"):
        if k in live and k != "pages_get":
            live[k]["body"] = live[k]["body"][:500]
    return {"spec": spec, "gh": gh, "local": local, "live": live}


# ───────────────────────── 판정 도우미 ─────────────────────────

def nodes(obj, key):
    return ((obj or {}).get(key) or {}).get("nodes") or []


def login_of(actor):
    return (actor or {}).get("login")


def commit_login(c):
    return login_of((c.get("author") or {}).get("user"))


def result(key, status, evidence, ai=False, score=None):
    full = POINTS[key]
    if score is None:
        score = {"pass": full, "na": full, "partial": (full + 1) // 2, "fail": 0, "human": 0}[status]
    return {"id": key, "title": TITLES[key], "points": full, "status": status, "score": score, "ai_check": ai, "evidence": evidence}


def linked_issue(pr):
    refs = [n["number"] for n in nodes(pr, "closingIssuesReferences")]
    if refs:
        return refs[0]
    for text in (pr["title"], pr["headRefName"]):
        m = re.search(r"#(\d+)", text or "")
        if m:
            return int(m.group(1))
    return None


def url(repo, kind, n):
    return f"https://github.com/{repo}/{kind}/{n}"


def feature_prs(gh, owner):
    """기능 PR = 본인이 올린, main.py를 고친 PR. 배포 준비(API_BASE 변경)는 index.html만 고치므로 빠진다."""
    out = []
    for pr in nodes(gh, "pullRequests"):
        if login_of(pr["author"]) != owner:
            continue
        if any(f["path"] == "main.py" for f in nodes(pr, "files")):
            out.append(pr)
    return out


def short(text, n=200):
    text = (text or "").strip().replace("\r", "")
    return text if len(text) <= n else text[:n] + "…"


def extract_function(src, name):
    m = re.search(rf"function\s+{name}\s*\(", src)
    if not m:
        return None
    i = src.find("{", m.end())
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start(): j + 1]
    return None


# ───────────────────────── 항목별 판정 ─────────────────────────

def check_flow(repo, gh, prs):
    issues = {i["number"]: i for i in nodes(gh, "issues")}
    merged = [p for p in prs if p["merged"]]
    if not merged:
        return result("W1", "fail", ["main.py를 고친 PR이 합쳐진 것이 없다"])
    ev, good = [], 0
    for pr in prs:
        n, bad = linked_issue(pr), []
        b = RE_BRANCH.match(pr["headRefName"])
        if not b or int(b.group(2)) != (n or -1):
            bad.append(f"Branch `{pr['headRefName']}`")
        if not RE_PR_TITLE.match(pr["title"]) or RE_PR_TITLE_TYPED.match(pr["title"]):
            bad.append("제목 형식(`[#번호] 내용`, type 없이)")
        issue = issues.get(n)
        if not nodes(pr, "closingIssuesReferences"):
            bad.append("`Closes #번호` 없음")
        elif pr["merged"] and not (issue and pr["number"] in [x["number"] for x in nodes(issue, "closedByPullRequestsReferences")]):
            bad.append(f"Issue #{n}이 이 PR로 닫히지 않음")
        mc = pr.get("mergeCommit") or {}
        if not pr["merged"]:
            bad.append("아직 합치지 않음")
        elif not (mc.get("parents", {}).get("totalCount") == 1 and (mc.get("messageHeadline") or "").endswith(f"(#{pr['number']})")):
            bad.append(f"Squash and merge 아님 (`{mc.get('messageHeadline')}`)")
        good += not bad
        ev.append(f"#{pr['number']} «{pr['title']}» " + ("— 규칙대로" if not bad else "— " + " · ".join(bad)))
    count_note = f"합쳐진 기능 PR {len(merged)}개" + (" (②③을 한 PR로 묶었을 수 있음)" if len(merged) == 3 else "")
    ev.insert(0, count_note)
    if len(merged) >= 3 and good == len(prs):
        return result("W1", "pass", ev)
    return result("W1", "partial", ev + (["기능 PR이 세 개보다 적다"] if len(merged) < 3 else []))


def check_commits(gh, prs, owner):
    commits = [(pr, n["commit"]) for pr in prs for n in nodes(pr, "commits")
               if n["commit"]["parents"]["totalCount"] < 2 and commit_login(n["commit"]) in (owner, None)]
    if not commits:
        return result("W2", "fail", ["기능 PR에 본인 Commit이 없다"])
    bad = []
    for pr, c in commits:
        m = RE_COMMIT.match(c["messageHeadline"])
        if not m or int(m.group(1)) != (linked_issue(pr) or -1):
            bad.append(f"PR #{pr['number']}: `{c['messageHeadline']}`")
    ev = [f"본인 Commit {len(commits)}개 중 규칙 위반 {len(bad)}개"] + bad
    if any(commit_login(c) is None for _, c in commits):
        ev.append("참고: Commit 이메일이 GitHub 계정과 연결되지 않았다")
    status = "pass" if not bad else "partial" if len(bad) <= len(commits) / 2 else "fail"
    return result("W2", status, ev)


def reviewers_of(prs, owner):
    out = []
    for pr in prs:
        for r in nodes(pr, "reviews"):
            who = login_of(r["author"])
            if who and who != owner and who not in out:
                out.append(who)
    return out


def check_review_received(prs, owner):
    if not prs:
        return result("W3", "fail", ["기능 PR이 없다"])
    ok, ev = 0, []
    for pr in prs:
        appr = [r for r in nodes(pr, "reviews") if r["state"] == "APPROVED" and login_of(r["author"]) != owner
                and (not pr["mergedAt"] or r["submittedAt"] <= pr["mergedAt"])]
        ok += bool(appr)
        ev.append(f"#{pr['number']}: " + (f"Approve by @{login_of(appr[0]['author'])}" if appr else "합치기 전 Pair의 Approve 없음"))
    status = "pass" if ok == len(prs) else "partial" if ok else "fail"
    return result("W3", status, ev)


def check_review_given(owner, partners, partner_repos):
    if not partners:
        return result("W4", "human", ["내 PR을 Review한 Pair가 없어 Pair의 Repository를 알 수 없다 — 사람 확인"])
    ev, total, done = [], 0, 0
    found = False
    for p in partners:
        gh = partner_repos.get(p)
        if not gh:
            ev.append(f"@{p}의 Repository를 찾지 못했다")
            continue
        found = True
        theirs = feature_prs(gh, p)
        for pr in theirs:
            total += 1
            mine = [r for r in nodes(pr, "reviews") if login_of(r["author"]) == owner]
            comments = [c["body"] for t in nodes(pr, "reviewThreads") for c in nodes(t, "comments") if login_of(c["author"]) == owner]
            done += bool(mine)
            line = f"{gh['nameWithOwner']} #{pr['number']}: " + (", ".join(sorted({r['state'] for r in mine})) if mine else "Review 없음")
            if mine and pr["mergedAt"] and min(r["submittedAt"] for r in mine) > pr["mergedAt"]:
                line += " (합친 뒤에 남김)"
            texts = [short(r["body"], 120) for r in mine if (r["body"] or "").strip()] + [short(c, 120) for c in comments]
            if texts:
                line += " — " + " / ".join(f"«{t}»" for t in texts[:3])
            ev.append(line)
    if not found:
        return result("W4", "human", ev + ["Pair의 Repository 주소를 목록에 넣으면 확인한다"])
    if total == 0:
        return result("W4", "human", ev + ["Pair의 기능 PR이 아직 없다"])
    status = "pass" if done / total >= 0.75 else "partial" if done else "fail"
    return result("W4", status, ev, ai=True)


def check_api(local):
    api = local.get("api")
    if api is None:
        return result("T1", "human", ["--no-run으로 실행하지 않았다"])
    if api.get("load_error", "") and api["load_error"].startswith("main.py에 DB 주소"):
        return result("T1", "human", [api["load_error"] + " — DB 주소를 환경변수로 옮긴 뒤 다시 채점하거나 사람이 확인 (D5에서 이미 감점)"])
    if api.get("load_error"):
        return result("T1", "fail", ["main.py를 불러오지 못했다: " + short(api["load_error"], 400)])
    res = api["results"]
    passed = sum(r["ok"] for r in res)
    ev = [f"{passed} / {len(res)} 통과"] + [f"✗ {r['name']} — {r['detail']}" for r in res if not r["ok"]]
    status = "pass" if passed == len(res) else "fail" if passed == 0 else "partial"
    return result("T1", status, ev, score=round(POINTS["T1"] * passed / max(len(res), 1)))


def check_fetch(local):
    src = local.get("index_html") or ""
    if not src:
        return result("T2", "fail", ["index.html이 없다"], ai=True)
    ok, ev = 0, []
    for name, needs in FUNCS.items():
        body = extract_function(src, name)
        if body is None:
            ev.append(f"✗ {name} — 함수를 찾지 못했다")
            continue
        missing = [n for n in needs if n.lower() not in body.lower()]
        if "아직 구현하지 않았습니다" in body:
            ev.append(f"✗ {name} — 아직 비어 있다")
            continue
        if missing:
            ev.append(f"✗ {name} — 빠진 것: {', '.join(missing)}\n```js\n{short(body, 600)}\n```")
            continue
        ok += 1
        ev.append(f"✓ {name}\n```js\n{short(body, 600)}\n```")
    status = "pass" if ok == 4 else "fail" if ok == 0 else "partial"
    return result("T2", status, [f"{ok} / 4 함수"] + ev, ai=True, score=round(POINTS["T2"] * ok / 4))


def check_render(live):
    base = live["api_base"]
    if not base:
        return result("D1", "fail", ["index.html에서 API_BASE를 찾지 못했다"])
    if "get" not in live:
        return result("D1", "fail", [f"API_BASE가 아직 `{base}` — Render 주소로 바꾸지 않았다"])
    g = live["get"]
    ev = [f"GET {base}/todos ({live['api_from']}) → {g['status'] or g.get('error')}"]
    if g["status"] == 200:
        if g.get("is_list"):
            return result("D1", "pass", ev)
        return result("D1", "partial", ev + ["응답이 TODO 배열이 아니다"])
    return result("D1", "fail", ev + ["서버가 꺼졌거나 주소가 틀렸다 — Render Logs 확인"])


def check_pages(live):
    if not live["pages"]:
        return result("D2", "human", ["Pages 주소를 찾지 못했다 — 목록에 pages=주소를 적거나, Repository의 Website 칸에 적게 한다"])
    g = live.get("pages_get") or {}
    ev = [f"GET {live['pages']} → {g.get('status') or g.get('error')}"]
    if g.get("status") != 200:
        return result("D2", "fail", ev)
    if 'id="new-form"' not in g["body"]:
        return result("D2", "partial", ev + ["응답이 TODO 화면(index.html)이 아니다"])
    m = RE_API_BASE.search(g["body"])
    served = m.group(1).rstrip("/") if m else None
    if served and live["api_base"] and served != live["api_base"]:
        return result("D2", "partial", ev + [f"Pages의 API_BASE(`{served}`)가 main의 것과 다르다 — 다시 배포되지 않았을 수 있음"])
    return result("D2", "pass", ev + [f"Pages의 API_BASE: `{served}`"])


def check_cors(live, local):
    if not live["pages"]:
        return result("D3", "human", ["Pages 주소가 없어 확인하지 못했다"])
    if "cors_get" not in live:
        return result("D3", "fail", ["배포한 API가 없어 확인하지 못했다 (D1)"])
    o = origin_of(live["pages"])
    acao_get = live["cors_get"]["headers"].get("access-control-allow-origin")
    acao_pre = live["cors_preflight"]["headers"].get("access-control-allow-origin")
    ev = [f"Origin {o} → GET 허락: `{acao_get}` · 사전 요청(OPTIONS, POST) {live['cors_preflight']['status']} 허락: `{acao_pre}`"]
    if local.get("main_py_has_star") or "*" in (acao_get, acao_pre):
        return result("D3", "partial", ev + ["`*`로 모든 주소를 허락했다 — README 2-5는 화면 주소만 허락하라고 한다"])
    if acao_get == o and acao_pre == o:
        return result("D3", "pass", ev)
    if live["cors_get"]["status"] is None:
        return result("D3", "fail", ev + ["API가 응답하지 않았다"])
    return result("D3", "fail", ev + ["ALLOWED_ORIGINS에 Pages 주소가 없다"])


def check_postgres():
    return result("D4", "human", ["GitHub · 공개 주소로는 어느 DB를 쓰는지 알 수 없다 — 학생에게 Supabase Table Editor에서 "
                                  "Pages로 등록한 TODO가 보이는지 확인 (확인되면 충족 5점)"])


def check_secrets(local):
    if local["secrets"]:
        return result("D5", "fail", ["🚨 비밀번호가 든 DB 주소가 Commit 이력에 있다 — 즉시 Supabase 비밀번호를 바꾸게 한다 "
                                     "(파일을 지워도 이력에 남는다)"] + local["secrets"])
    if local["risky_files"]:
        return result("D5", "partial", [f"올리지 말아야 할 파일이 이력에 있다: {', '.join(local['risky_files'])}"])
    return result("D5", "pass", ["모든 Branch의 이력에서 DB 비밀번호를 찾지 못했다"])


# ───────────────────────── 한 사람 채점 ─────────────────────────

def grade(raw, partner_index):
    gh, local, live = raw["gh"], raw["local"], raw["live"]
    repo, owner = gh["nameWithOwner"], gh["owner"]["login"]
    prs = feature_prs(gh, owner)
    partners = reviewers_of(prs, owner)
    partner_repos = {p: partner_index.get(p) for p in partners}
    items = [
        check_flow(repo, gh, prs),
        check_commits(gh, prs, owner),
        check_review_received(prs, owner),
        check_review_given(owner, partners, partner_repos),
        check_api(local),
        check_fetch(local),
        check_render(live),
        check_pages(live),
        check_cors(live, local),
        check_postgres(),
        check_secrets(local),
    ]
    history = (((gh.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes") or []
    direct = [c for c in history[:-1] if not nodes(c, "associatedPullRequests")]
    penalty = DIRECT_PUSH_PENALTY if direct else 0
    total = max(0, sum(i["score"] for i in items) - penalty)
    pending = sum(i["points"] for i in items if i["status"] == "human")
    return {
        "repo": repo, "ref": raw["spec"].get("ref"), "login": owner, "items": items,
        "penalty": {"points": penalty, "evidence": [f"`{c['messageHeadline']}` ({c['oid'][:7]})" for c in direct]},
        "total": total, "pending_points": pending,
        "verdict": "완료" if total >= PASS_SCORE and not any(i["status"] == "fail" for i in items) else "보완",
    }


MARK = {"pass": "충족", "partial": "부분", "fail": "미충족", "na": "해당 없음", "human": "사람 확인"}


def to_markdown(graded):
    out = ["| 저장소 | 아이디 | 점수 | 사람 확인 대기 | 판정 |", "|---|---|---|---|---|"]
    for g in graded:
        out.append(f"| {g['repo']}{'@' + g['ref'] if g['ref'] else ''} | @{g['login']} | {g['total']} | {g['pending_points']}점 | {g['verdict']} |")
    out.append("")
    for g in graded:
        out.append(f"## @{g['login']} — {g['repo']} — {g['total']} / 100 · {g['verdict']}"
                   + (f" (사람 확인 {g['pending_points']}점 대기)" if g["pending_points"] else "") + "\n")
        out.append("| 항목 | 배점 | 판정 | 점수 | 근거 |\n|---|---|---|---|---|")
        for i in g["items"]:
            ev = "<br>".join(e.replace("\n", "<br>").replace("|", "\\|") for e in i["evidence"])
            ai = " · AI 확인" if i["ai_check"] else ""
            out.append(f"| {i['id']} {i['title']} | {i['points']} | {MARK[i['status']]}{ai} | {i['score']} | {ev} |")
        if g["penalty"]["points"]:
            out.append(f"| 감점 · main 직접 Push | −{g['penalty']['points']} | | | {'<br>'.join(g['penalty']['evidence'])} |")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="onboarding-todo 실습 채점")
    ap.add_argument("repos", nargs="*", help="아이디/onboarding-todo [pages=주소] [api=주소]")
    ap.add_argument("--list", help="한 줄에 한 사람씩 적은 파일")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--no-run", action="store_true", help="학생의 main.py를 실행하지 않는다 (T1은 사람 확인)")
    ap.add_argument("--raw-out", help="모은 원자료를 저장")
    ap.add_argument("--from-json", help="저장해 둔 원자료로 다시 채점 (GitHub · 서비스에 묻지 않음)")
    a = ap.parse_args()

    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            bundle = json.load(f)
    else:
        lines = []
        if a.repos:
            # 인자: 저장소 뒤에 오는 key=value는 그 저장소의 옵션
            cur = []
            for tok in a.repos:
                if "=" in tok and cur:
                    cur.append(tok)
                else:
                    if cur:
                        lines.append(" ".join(cur))
                    cur = [tok]
            if cur:
                lines.append(" ".join(cur))
        if a.list:
            with open(a.list, encoding="utf-8") as f:
                lines += [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
        if not lines:
            ap.error("저장소를 하나 이상 주세요")
        specs = [parse_spec(l) for l in lines]
        raws = []
        for s in specs:
            print(f"… {s['repo']} 확인 중", file=sys.stderr)
            raws.append(collect(s, run_tests=not a.no_run))
        # Pair의 Repository: 목록에 있으면 그것을, 없으면 같은 이름으로 찾아본다
        partners = {r["gh"]["owner"]["login"]: r["gh"] for r in raws}
        for r in raws:
            owner = r["gh"]["owner"]["login"]
            for p in reviewers_of(feature_prs(r["gh"], owner), owner):
                if p not in partners:
                    gh, _ = gh_repo(f"{p}/{r['gh']['name']}")
                    partners[p] = gh
        bundle = {"repos": raws, "partners": partners}
        if a.raw_out:
            with open(a.raw_out, "w", encoding="utf-8") as f:
                json.dump(bundle, f, ensure_ascii=False, indent=1)

    graded = [grade(r, bundle["partners"]) for r in bundle["repos"]]
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(graded, ensure_ascii=False, indent=1) if a.format == "json" else to_markdown(graded))


if __name__ == "__main__":
    main()
