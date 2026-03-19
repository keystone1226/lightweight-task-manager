# Lightweight Task Manager - 구현 계획

## 프로젝트 개요
외부망과 단절된 환경에서 팀원들이 가볍게 사용할 수 있는 일감관리 도구.
서버 실행 시 로컬 IP에 바인딩하여 같은 네트워크의 팀원들과 공유.

## 기술 스택
- **Backend**: Python + FastAPI (단일 파일로 시작, 의존성 최소화)
- **Frontend**: 순수 HTML/CSS/JS (별도 빌드 불필요, Jinja2 템플릿 또는 정적 파일)
- **Database**: SQLite (파일 기반, 설치 불필요)
- **Migration**: Alembic (스키마 버전 관리 + 자동 마이그레이션)
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

## DB 마이그레이션 전략

30명 규모의 팀이 지속적으로 사용하는 환경에서, 앱 업데이트 시 기존 데이터가 안전하게 보존되어야 함.

### 핵심 원칙
- **Alembic**으로 스키마 버전 관리 — 모든 DB 변경은 마이그레이션 파일로 추적
- **서버 시작 시 자동 마이그레이션** — 관리자가 별도 명령을 실행할 필요 없음
- **하위 호환성** — 새 컬럼 추가 시 반드시 default 값 지정, 기존 데이터 유지

### 마이그레이션 흐름
```
[앱 업데이트] → [서버 시작] → [Alembic 자동 실행] → [DB 스키마 최신화] → [서비스 정상 운영]
```

### 구체적 동작
1. **서버 시작 시**: `alembic upgrade head`가 자동 실행됨
2. **신규 설치**: 빈 DB에 최신 스키마가 한번에 생성됨
3. **기존 운영 중 업데이트**: 누적된 마이그레이션이 순서대로 적용됨
4. **롤백 필요 시**: `alembic downgrade -1`로 이전 버전으로 복원 가능

### 마이그레이션 작성 규칙
- 새 컬럼 추가 시 `server_default` 필수 (기존 행에 NULL 방지)
- 컬럼 삭제 대신 deprecate 후 다음 버전에서 제거 (2단계 삭제)
- 데이터 변환이 필요한 경우 `op.execute()`로 data migration 포함
- 각 마이그레이션 파일에 변경 사유 주석 작성

### 백업
- 서버 시작 시 마이그레이션 실행 전 `tasks.db`를 `tasks.db.bak.{timestamp}`로 자동 백업
- 마이그레이션 실패 시 백업 파일에서 복원 안내 메시지 출력

## 디렉토리 구조

```
task-manager/
├── app/
│   ├── main.py           # FastAPI 앱 엔트리포인트 + IP 바인딩
│   ├── models.py          # SQLModel 데이터 모델
│   ├── database.py        # DB 연결 설정 + 자동 마이그레이션
│   ├── routers/
│   │   └── tasks.py       # 태스크 API 라우터
│   └── static/
│       ├── index.html     # SPA 메인 페이지 (칸반 보드)
│       ├── style.css      # 스타일
│       └── app.js         # 프론트엔드 로직
├── alembic/
│   ├── env.py             # Alembic 환경 설정
│   └── versions/          # 마이그레이션 파일들
├── alembic.ini            # Alembic 설정
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
3. **Alembic 설정 + 초기 마이그레이션**
4. **서버 시작 시 자동 마이그레이션 + DB 백업 로직**
5. API 라우터 구현
6. 프론트엔드 칸반 보드 UI
7. IP 자동 감지 + 서버 실행 로직
8. README 작성 (마이그레이션/업데이트 가이드 포함)
