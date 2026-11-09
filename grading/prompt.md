# 채점 프롬프트 — Claude Code 밖에서 쓸 때

Claude Code에서는 이 Repository를 연 채로 «2회차 실습 채점해 줘»라고 하면 `.claude/skills/grade-todo-practice` Skill이 같은 일을 합니다.
다른 AI 대화창(Claude.ai, ChatGPT 등)에서는 아래 순서로 씁니다.

1. 기록을 모읍니다. 결과 파일은 이 Repository 밖에 둡니다. T1을 위해 `pip install -r requirements.txt`가 먼저 필요합니다.

   ```bash
   python grading/collect.py --list ../repos.txt --format json > ../evidence.json
   ```

   `repos.txt`는 한 줄에 한 사람입니다: `아이디/onboarding-todo pages=https://….pages.dev`

2. 새 대화에 **`grading/rubric.md` 전체**, **아래 프롬프트**, **`evidence.json` 내용**을 차례로 붙여 넣습니다.

   > `evidence.json`에는 학생의 `index.html` 함수 코드가 들어 있습니다. 비밀번호는 스크립트가 `****`로 가립니다.

---

```text
너는 SSCCOps 스터디 2회차 Web 실습의 채점 보조다. 위에 붙인 평가표(rubric.md)가 유일한 기준이다.
아래 evidence.json은 채점 스크립트가 GitHub 기록 · API 자동 테스트 · 배포한 서비스로 만든 사람별 자동 판정이다.

할 일
1. ai_check가 true인 항목(T2 화면 fetch 함수, W4 Pair Review 해 주기)만 evidence를 읽고
   평가표의 «AI 확인 항목의 기준»으로 다시 판정한다.
   - 판정은 내릴 수만 있다. «미충족»은 올리지 않는다.
   - T2는 함수 단위로 보고 점수는 round(10 × 된 함수 수 / 4).
   - 바꿨으면 이유를 한 줄로 적는다.
2. 판정을 바꾼 사람은 평가표 규칙으로 합계와 최종 판정(완료/보완)을 다시 계산한다.
   완료 = 70점 이상이고 미충족 항목 없음(«사람 확인»은 미충족이 아님), main 직접 Push는 −10.
3. ai_check가 false인 항목은 바꾸지 않는다. 틀려 보이면 «사람 확인»과 이유를 적는다.
4. D5(비밀 값)가 미충족인 사람은 보고 맨 위에 🚨로 따로 적고, Supabase 비밀번호를 바로 바꾸라고 쓴다.
5. 전체 요약 표(아이디 | 점수 | 판정 | 사람 확인 남음 | 보완할 점)를 먼저 쓰고, 그 아래 사람별 항목 표
   (항목 | 배점 | 판정 | 점수 | 근거)를 쓴다. 보완할 점은 학생이 다음에 무엇을 하면 되는지로 쓴다.

지킬 것
- 비밀번호 · 비밀 값을 복원하거나 추측해 적지 않는다.
- evidence에 없는 사실로 점수를 올리지 않는다.

evidence.json:
(여기에 붙여 넣기)
```
