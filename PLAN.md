# Lightweight Task Manager - 구현 계획

## 프로젝트 개요
외부망과 단절된 환경에서 팀원들이 가볍게 사용할 수 있는 일감관리 도구.
서버 실행 시 로컬 IP에 바인딩하여 같은 네트워크의 팀원들과 공유.

## 기술 스택
- **Backend**: Python + FastAPI (단일 파일로 시작, 의존성 최소화)
- **Frontend**: 순수 HTML/CSS/JS (별도 빌드 불필요, Jinja2 템플릿 또는 정적 파일)
- **Database**: SQLite (파일 기반, 설치 불필요)
- **패키지 관리**: uv + pyproject.toml

> 외부망 단절 환경을 고려하여 CDN 의존 없이 모든 에셋을 로컬에 포함

## 핵심 기능

### 1단계: MVP
- [ ] **태스크 CRUD** - 생성, 조회, 수정, 삭제
- [ ] **태스크 상태관리** - TODO → IN_PROGRESS → DONE (칸반 보드 UI)
- [ ] **담당자 지정** - 간단한 닉네임 기반 (로그인 없이)
- [ ] **우선순위** - 높음 / 보통 / 낮음
- [ ] **IP 바인딩** - 서버 실행 시 자동으로 로컬 IP 감지 + 수동 지정 옵션

### 2단계: 확장 (향후)
- [ ] 프로젝트/보드 분리
- [ ] 태스크 코멘트
- [ ] 간단한 검색/필터
- [ ] 데이터 내보내기 (JSON/CSV)

## 디렉토리 구조

```
task-manager/
├── app/
│   ├── main.py           # FastAPI 앱 엔트리포인트 + IP 바인딩
│   ├── models.py          # SQLModel 데이터 모델
│   ├── database.py        # DB 연결 설정
│   ├── routers/
│   │   └── tasks.py       # 태스크 API 라우터
│   └── static/
│       ├── index.html     # SPA 메인 페이지 (칸반 보드)
│       ├── style.css      # 스타일
│       └── app.js         # 프론트엔드 로직
├── pyproject.toml         # 프로젝트 설정 + 의존성
├── README.md              # 사용법
└── tasks.db               # SQLite DB (자동 생성)
```

## 데이터 모델

### Task
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int (PK) | 자동 증가 |
| title | str | 태스크 제목 |
| description | str (optional) | 상세 설명 |
| status | enum | TODO / IN_PROGRESS / DONE |
| priority | enum | HIGH / MEDIUM / LOW |
| assignee | str (optional) | 담당자 닉네임 |
| created_at | datetime | 생성 시간 |
| updated_at | datetime | 수정 시간 |

## API 설계

| Method | Path | 설명 |
|--------|------|------|
| GET | /api/tasks | 전체 태스크 조회 |
| POST | /api/tasks | 태스크 생성 |
| PATCH | /api/tasks/{id} | 태스크 수정 |
| DELETE | /api/tasks/{id} | 태스크 삭제 |
| PATCH | /api/tasks/{id}/status | 상태 변경 (드래그앤드롭) |
| GET | / | 칸반 보드 UI |

## UI 설계
- **칸반 보드 레이아웃**: 3개 컬럼 (TODO / IN PROGRESS / DONE)
- **드래그 앤 드롭**: HTML5 Drag & Drop API (라이브러리 없이)
- **태스크 카드**: 제목, 우선순위 뱃지, 담당자 표시
- **모달**: 태스크 생성/수정용 폼
- **반응형**: 기본적인 모바일 대응

## 실행 방법 (목표)
```bash
# 의존성 설치
uv sync

# 서버 실행 (자동 IP 감지)
uv run python -m app.main

# 또는 IP 수동 지정
uv run python -m app.main --host 192.168.1.100 --port 8000
```

실행 시 콘솔에 접속 URL 출력:
```
🚀 Task Manager 실행 중
📡 http://192.168.1.100:8000
팀원들에게 위 URL을 공유하세요!
```

## 구현 순서
1. 프로젝트 초기화 (pyproject.toml, 디렉토리 구조)
2. 데이터 모델 + DB 설정
3. API 라우터 구현
4. 프론트엔드 칸반 보드 UI
5. IP 자동 감지 + 서버 실행 로직
6. README 작성
