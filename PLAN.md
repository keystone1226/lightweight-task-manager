# Lightweight Task Manager - 구현 계획

## 프로젝트 개요
외부망과 단절된 환경에서 디자이너 팀(~30명)이 가볍게 사용할 수 있는 일감관리 도구.
서버 실행 시 로컬 IP에 바인딩하여 같은 네트워크의 팀원들과 공유.

## 기술 스택
- **Backend**: Python + FastAPI (의존성 최소화)
- **Frontend**: 순수 HTML/CSS/JS (별도 빌드 불필요)
- **Database**: SQLite (파일 기반, 설치 불필요)
- **Migration**: Alembic (스키마 버전 관리 + 자동 마이그레이션)
- **패키지 관리**: uv + pyproject.toml

> 외부망 단절 환경을 고려하여 CDN 의존 없이 모든 에셋을 로컬에 포함

## 핵심 기능

### 1단계: MVP
- [ ] **태스크 CRUD** - 생성, 조회, 수정, 삭제
- [ ] **태스크 상태관리** - 커스텀 컬럼 지원 칸반 보드 (기본: TODO / IN_PROGRESS / REVIEW / DONE)
- [ ] **우선순위** - 높음 / 보통 / 낮음
- [ ] **닉네임 기반 사용자** - 최초 접속 시 닉네임 입력, localStorage 저장
- [ ] **담당자 지정** - 등록된 닉네임 목록에서 선택
- [ ] **링크 필드** - 피그마/컨플루언스 URL 전용 필드, 아이콘 자동 인식
- [ ] **이미지 첨부** - 태스크 카드에 스크린샷/시안 첨부 (로컬 서버 업로드)
- [ ] **컬러 태그** - "UI", "아이콘", "리서치", "QA" 등 색상별 태그
- [ ] **마감일** - Due date + 기한 임박 시 시각적 강조
- [ ] **코멘트** - 태스크별 대화, @멘션 지원
- [ ] **알림** - 접속 시 "나에게 온 멘션 N건" 배지
- [ ] **IP 바인딩** - 서버 실행 시 자동 IP 감지 + 수동 지정 옵션
- [ ] **이메일 알림 (선택)** - 사내 SMTP 설정 시 멘션/상태변경 이메일 발송

### 2단계: 확장 (향후)
- [ ] 프로젝트/보드 분리
- [ ] 간단한 검색/필터
- [ ] 데이터 내보내기 (JSON/CSV)

## 사용자 관리

### 닉네임 기반 (로그인 없음)
1. 최초 접속 시 "닉네임을 입력하세요" 팝업
2. 브라우저 localStorage에 저장 → 다음 접속 시 자동 인식
3. 서버에 닉네임 + 이메일(선택) 저장 → @멘션 자동완성 제공
4. 접속 시 본인에게 온 멘션 확인 가능

## DB 마이그레이션 전략

30명 규모 팀이 지속 사용하는 환경에서, 앱 업데이트 시 기존 데이터 안전 보존.

### 핵심 원칙
- **Alembic**으로 스키마 버전 관리 — 모든 DB 변경은 마이그레이션 파일로 추적
- **서버 시작 시 자동 마이그레이션** — 관리자가 별도 명령 불필요
- **하위 호환성** — 새 컬럼 추가 시 반드시 default 값 지정

### 마이그레이션 흐름
```
[앱 업데이트] → [서버 시작] → [DB 백업] → [Alembic 자동 실행] → [서비스 정상 운영]
```

### 백업
- 마이그레이션 실행 전 `tasks.db` → `tasks.db.bak.{timestamp}` 자동 백업
- 실패 시 백업에서 복원 안내 메시지 출력

## 디렉토리 구조

```
task-manager/
├── app/
│   ├── __init__.py
│   ├── __main__.py        # python -m app 엔트리포인트
│   ├── main.py            # FastAPI 앱 + 서버 실행
│   ├── models.py          # SQLModel 데이터 모델
│   ├── database.py        # DB 연결 + 자동 마이그레이션
│   ├── config.py          # 설정 (SMTP 등)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── tasks.py       # 태스크 API
│   │   ├── comments.py    # 코멘트 API
│   │   ├── users.py       # 사용자(닉네임) API
│   │   └── notifications.py # 알림 API
│   ├── services/
│   │   └── email.py       # 이메일 발송 (선택적)
│   ├── static/
│   │   ├── index.html     # 칸반 보드 SPA
│   │   ├── style.css
│   │   └── app.js
│   └── uploads/           # 이미지 첨부 파일 저장
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── pyproject.toml
└── README.md
```

## 데이터 모델

### User
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int (PK) | 자동 증가 |
| nickname | str (unique) | 닉네임 |
| email | str (optional) | 이메일 (SMTP 알림용) |
| created_at | datetime | 등록 시간 |

### Task
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int (PK) | 자동 증가 |
| title | str | 태스크 제목 |
| description | str (optional) | 상세 설명 |
| status | str | 상태 (컬럼명) |
| priority | enum | HIGH / MEDIUM / LOW |
| assignee_id | int (FK, optional) | 담당자 |
| figma_url | str (optional) | 피그마 링크 |
| confluence_url | str (optional) | 컨플루언스 링크 |
| image_path | str (optional) | 첨부 이미지 경로 |
| due_date | date (optional) | 마감일 |
| tags | str (optional) | JSON 배열로 태그 저장 |
| sort_order | int | 칸반 보드 내 정렬 순서 |
| created_at | datetime | 생성 시간 |
| updated_at | datetime | 수정 시간 |

### Comment
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int (PK) | 자동 증가 |
| task_id | int (FK) | 소속 태스크 |
| author_id | int (FK) | 작성자 |
| content | str | 내용 (@멘션 포함) |
| created_at | datetime | 작성 시간 |

### Notification
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int (PK) | 자동 증가 |
| user_id | int (FK) | 대상 사용자 |
| task_id | int (FK) | 관련 태스크 |
| type | str | mention / status_change / assignment |
| message | str | 알림 내용 |
| is_read | bool | 읽음 여부 |
| created_at | datetime | 생성 시간 |

### BoardColumn
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int (PK) | 자동 증가 |
| name | str | 컬럼명 |
| sort_order | int | 표시 순서 |
| color | str (optional) | 컬럼 색상 |

## API 설계

| Method | Path | 설명 |
|--------|------|------|
| GET | /api/tasks | 전체 태스크 조회 |
| POST | /api/tasks | 태스크 생성 |
| PATCH | /api/tasks/{id} | 태스크 수정 |
| DELETE | /api/tasks/{id} | 태스크 삭제 |
| PATCH | /api/tasks/{id}/status | 상태 변경 (드래그앤드롭) |
| POST | /api/tasks/{id}/image | 이미지 첨부 |
| GET | /api/tasks/{id}/comments | 코멘트 조회 |
| POST | /api/tasks/{id}/comments | 코멘트 작성 |
| POST | /api/users | 닉네임 등록 |
| GET | /api/users | 사용자 목록 (멘션 자동완성) |
| GET | /api/users/{id}/notifications | 알림 목록 |
| PATCH | /api/notifications/{id}/read | 알림 읽음 처리 |
| GET | /api/columns | 보드 컬럼 목록 |
| POST | /api/columns | 컬럼 추가 |
| PATCH | /api/columns/{id} | 컬럼 수정 |
| DELETE | /api/columns/{id} | 컬럼 삭제 |
| GET | / | 칸반 보드 UI |
| GET | /uploads/{filename} | 첨부 이미지 서빙 |

## 구현 순서
1. 프로젝트 초기화 (pyproject.toml, 디렉토리 구조)
2. 데이터 모델 + DB 설정
3. Alembic 설정 + 초기 마이그레이션
4. 서버 시작 시 자동 마이그레이션 + DB 백업
5. API 라우터 구현 (tasks, comments, users, notifications, columns)
6. 프론트엔드 칸반 보드 UI
7. IP 자동 감지 + 서버 실행 로직
8. 이메일 알림 서비스 (선택적)
9. README 작성
