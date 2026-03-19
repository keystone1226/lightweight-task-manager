# Handoff — 2026-03-19

이 문서는 Claude Code CLI 세션에서 작업한 내용을 다음 세션에서 이어받기 위해 작성됨.

---

## 프로젝트 개요

**lightweight-task-manager** — 외부망 단절 환경의 디자이너 팀(~30명)을 위한 칸반 태스크 관리 도구.
설치 없이 `uv run python -m app` 한 줄로 실행, 팀원들이 같은 네트워크에서 브라우저로 접속해서 사용.

**실행 방법**
```bash
cd task-manager
uv sync
uv run python -m app
# → http://localhost:8000
```

---

## 오늘 작업한 것들

### 1. URL 필드 통합 + OG 미리보기
- `figma_url` + `confluence_url` → `link_url` 하나로 통합 (Alembic 마이그레이션 포함)
- `GET /api/og-preview?url=...` 엔드포인트 추가
- URL 입력 후 800ms debounce → og:title, og:image, og:description 미리보기 카드 표시
- 서버사이드 fetch (CORS 우회), 실패 시 조용히 무시

### 2. 주간보고 사이드바
- 헤더 "📋 주간보고" 버튼 → 오른쪽 슬라이드인 사이드바
- `task_history` 테이블 추가: 상태/담당자/우선순위 변경 시 자동 기록
- `GET /api/report/weekly-tasks?year=&week=` — 해당 주에 변경된 태스크 전체
- `POST /api/report/generate` — 선택된 태스크 + 과거 보고서 예시 → LLM 호출
- 최근 6주 드롭다운, 태스크 체크리스트(기본 전체 선택), 재생성 버튼, 복사 버튼
- **⚠️ LLM 미완성**: 사무실에서 내부 LLM API 확인 후 `.env` 설정 필요

### 3. 댓글 삭제
- `DELETE /api/comments/{id}?requester_id={id}` — author_id 불일치 시 403
- 본인 댓글에만 hover 시 ✕ 버튼 표시

---

## ⚠️ 남은 작업

### 주간보고 LLM 연동 완성 (최우선)
사무실에서 확인 후 `.env` 파일에 추가:
```bash
TASK_LLM_URL=https://내부LLM주소/v1/chat/completions
TASK_LLM_TOKEN=Bearer_토큰값
TASK_LLM_MODEL=모델명
```
- API가 OpenAI 호환 포맷(`choices[0].message.content`)인지 확인 필요
- 포맷이 다르면 `routers/report.py`의 `generate_report()` 응답 파싱 부분 수정

### 서버 재시작 필요
오늘 배포한 코드(report, og-preview 등)가 아직 반영 안 됨:
```bash
# 실행 중인 서버 Ctrl+C 후
uv run python -m app
```
재시작 시 Alembic이 `task_history` 테이블 자동 생성.

---

## 파일 구조 (핵심만)

```
task-manager/
├── app/
│   ├── config.py          ← LLM 환경변수 설정 위치
│   ├── models.py          ← Task, TaskHistory, User 등
│   ├── routers/
│   │   ├── tasks.py       ← 태스크 CRUD + 히스토리 기록
│   │   ├── comments.py    ← 댓글 CRUD + 삭제
│   │   ├── report.py      ← 주간보고 API ← 여기 수정
│   │   └── og.py          ← OG 미리보기
│   └── static/
│       ├── app.js         ← 프론트엔드 전체 로직
│       └── index.html     ← UI 구조
└── alembic/versions/      ← DB 마이그레이션 이력
```

---

## GitHub

- repo: https://github.com/keystone1226/lightweight-task-manager
- branch: main (모든 작업 push 완료)

---

## 내일 이어서 할 때

1. `HANDOFF.md` 이 파일을 Claude에게 읽혀주면 컨텍스트 복원됨
2. LLM API 정보 확인 후 `.env` 세팅
3. 내부 LLM 응답 포맷이 OpenAI 호환이 아니면 `report.py` 수정
