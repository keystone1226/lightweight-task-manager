# Lightweight Task Manager

외부망이 없는 환경에서 디자이너 팀(~30명)이 가볍게 쓸 수 있는 칸반 태스크 관리 도구.
설치 없이 서버를 실행하면 같은 네트워크 팀원 모두가 브라우저로 접속해서 바로 사용할 수 있다.

---

## 빠른 시작

```bash
cd task-manager

# 의존성 설치
uv sync

# 서버 실행
uv run python -m app
```

실행하면 다음과 같이 출력된다:

```
==================================================
  Task Manager
==================================================
  Local:   http://127.0.0.1:8000
  Network: http://192.168.1.100:8000

  Share the Network URL with your team!
==================================================
```

**Network URL**을 팀원들에게 공유하면 끝. 팀원들은 브라우저에서 URL을 열고 닉네임을 입력하면 바로 사용 가능.

### 포트 변경

```bash
uv run python -m app --host 0.0.0.0 --port 9000
```

---

## 사용 방법

### 1. 접속 & 닉네임 등록

처음 접속하면 닉네임 입력 팝업이 뜬다. 닉네임을 입력하면 브라우저에 저장되어 다음 접속 시 자동으로 인식된다. 로그인 없이 닉네임만으로 동작한다.

### 2. 칸반 보드

기본 컬럼: `TODO → IN PROGRESS → REVIEW → DONE`

- 카드를 드래그해서 컬럼 간 이동
- 컬럼은 자유롭게 추가/삭제/이름 변경 가능

### 3. 태스크 카드

카드를 클릭하면 상세 편집 화면이 열린다:

| 필드 | 설명 |
|------|------|
| 제목 / 설명 | 태스크 내용 |
| 담당자 | 등록된 팀원 목록에서 선택 |
| 우선순위 | 높음 / 보통 / 낮음 |
| 마감일 | 기한 임박 시 카드에 시각적 강조 표시 |
| 컬러 태그 | UI, 아이콘, 리서치, QA 등 색상 태그 |
| Figma URL | Figma 링크 (아이콘 자동 인식) |
| Confluence URL | Confluence 링크 (아이콘 자동 인식) |
| 이미지 첨부 | 스크린샷/시안 업로드 → 카드 커버로 표시 |

### 4. 코멘트 & @멘션

태스크 상세에서 코멘트 작성 가능. `@닉네임`으로 멘션하면 해당 팀원에게 알림이 간다.

### 5. 알림

상단 알림 아이콘에 읽지 않은 알림 수가 표시된다:
- 태스크 배정됨
- 태스크 상태 변경
- 코멘트에서 @멘션됨

---

## 이메일 알림 (선택)

사내 SMTP 서버가 있으면 멘션/배정 시 이메일 알림을 보낼 수 있다.

```bash
export TASK_SMTP_HOST=mail.company.internal
export TASK_SMTP_PORT=25
export TASK_SMTP_FROM=taskmanager@company.com
export TASK_SMTP_USER=        # 인증 없으면 비워둠
export TASK_SMTP_PASSWORD=    # 인증 없으면 비워둠
```

또는 `task-manager/` 디렉토리에 `.env` 파일로 저장:

```bash
cp .env.example .env
# .env 파일을 열어서 값 입력
```

---

## 데이터베이스

- SQLite 파일(`tasks.db`)이 자동으로 생성됨 — 별도 DB 설치 불필요
- 서버 시작 시 스키마 마이그레이션 자동 실행
- 마이그레이션 전 자동 백업: `tasks.db.bak.{timestamp}`
- 수동 롤백이 필요하면: `uv run alembic downgrade -1`

---

## 기술 스택

| 구성 | 내용 |
|------|------|
| Backend | Python 3.10+ / FastAPI / SQLModel / Alembic |
| Frontend | HTML / CSS / JS (빌드 없음, CDN 없음) |
| Database | SQLite |
| 패키지 관리 | uv |

> 외부망 단절 환경을 위해 CDN 의존 없이 모든 에셋이 로컬에 포함되어 있다.

---

## 디렉토리 구조

```
task-manager/
├── app/
│   ├── main.py            # FastAPI 앱 + 서버 실행 (IP 자동 감지)
│   ├── models.py          # 데이터 모델 (Task, User, Comment, Notification)
│   ├── database.py        # DB 연결 + 자동 마이그레이션
│   ├── config.py          # 설정 (포트, SMTP 등)
│   ├── routers/
│   │   ├── tasks.py       # 태스크 CRUD API
│   │   ├── comments.py    # 코멘트 API
│   │   ├── users.py       # 사용자(닉네임) API
│   │   ├── columns.py     # 칸반 컬럼 API
│   │   └── notifications.py
│   ├── services/
│   │   └── email.py       # 이메일 알림 (선택)
│   └── static/
│       ├── index.html     # 칸반 보드 SPA
│       ├── style.css
│       └── app.js
├── alembic/               # DB 마이그레이션 파일
├── pyproject.toml
└── README.md
```

---

## API 엔드포인트

서버 실행 후 `http://localhost:8000/docs`에서 Swagger UI로 전체 API를 확인할 수 있다.

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/tasks` | 태스크 목록 |
| POST | `/api/tasks` | 태스크 생성 |
| PATCH | `/api/tasks/{id}` | 태스크 수정 |
| DELETE | `/api/tasks/{id}` | 태스크 삭제 |
| PATCH | `/api/tasks/{id}/status` | 상태 변경 (드래그앤드롭) |
| POST | `/api/tasks/{id}/image` | 이미지 첨부 |
| GET | `/api/users` | 사용자 목록 |
| POST | `/api/users` | 닉네임 등록 |
| GET | `/api/columns` | 보드 컬럼 목록 |
| GET | `/api/users/{id}/notifications` | 알림 목록 |
