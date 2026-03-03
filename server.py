"""
Interview Analyzer - Local Proxy Server
환경변수 ANTHROPIC_API_KEY를 읽어 Anthropic API를 호출합니다.
긴 녹취록은 자동으로 청크 분할하여 분석 후 병합합니다.
"""
import os
import json
import re
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
PORT     = 5500
MODEL    = "claude-sonnet-4-6"
MAX_OUT  = 8192          # 모델 최대 출력 토큰
# 1청크당 최대 단어 수 (약 4500 한국어 단어 ≈ 6000 토큰 입력)
CHUNK_WORDS = 4000


# ──────────────────────────────────────────────
# Claude API 호출
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior UX researcher. Extract structured information from interview transcripts.
Always respond with valid JSON ONLY — no markdown fences, no preamble, no explanation.
The JSON must strictly follow the schema provided by the user."""

def build_user_message(transcript: str, options: dict = None) -> str:
    if options is None:
        options = {}

    clustering    = options.get("clustering", "normal")
    include_flows = options.get("include_flows", True)
    focus         = options.get("focus", "balanced")

    # Max item counts by clustering level
    max_q  = {"fine": 12, "normal": 8, "coarse": 5}.get(clustering, 8)
    max_pp = {"fine": 12, "normal": 8, "coarse": 5}.get(clustering, 8)
    max_nd = {"fine": 12, "normal": 8, "coarse": 6}.get(clustering, 8)

    clustering_hint = {
        "fine":   "유사한 항목도 각각 별도 항목으로 세밀하게 분리 추출",
        "normal": "적절한 수준으로 유사 항목 클러스터링",
        "coarse": "유사한 항목을 하나로 묶어 핵심 위주로만 추출",
    }.get(clustering, "적절한 수준으로 유사 항목 클러스터링")

    if focus == "pain":
        focus_hint = "페인포인트 분석에 집중. 질문은 핵심 4개 이하로 최소화. 플로우는 없으면 생략."
    elif focus == "flow":
        focus_hint = "사용자 행동 플로우 다이어그램에 집중. 프로세스를 상세히 표현. 질문·페인포인트는 최소화."
    else:
        focus_hint = "질문·페인포인트·플로우를 균형 있게 분석."

    if include_flows:
        flows_schema = f"""  "flows": [
    {{
      "id": "flow_1",
      "title": "플로우 제목",
      "nodes": [
        {{ "id": "n1", "label": "단계명 (8자 이내)", "type": "Start|Process|Decision|End", "description": "" }}
      ],
      "edges": [
        {{ "id": "e1", "source": "n1", "target": "n2", "label": "" }}
      ]
    }}
  ]"""
        flows_rule = f"- flows: 명확한 프로세스가 있을 경우만 포함 (없으면 []), 노드 최대 {max_nd}개"
    else:
        flows_schema = '  "flows": []'
        flows_rule   = "- flows: 항상 [] (플로우 분석 제외)"

    return f"""아래 인터뷰 녹취록을 분석해서 다음 JSON 스키마에 맞춰 정리해줘.
JSON만 출력하고, 다른 텍스트(마크다운 포함)는 절대 출력하지 마.

=== 분석 설정 ===
- 클러스터링: {clustering_hint}
- 집중 영역: {focus_hint}

=== JSON 스키마 ===
{{
  "interview_title": "인터뷰의 핵심 주제를 담은 간결한 제목 (20자 이내)",
  "questions": [
    {{ "id": "q_1", "text": "인터뷰어의 주요 질문 내용", "category": "배경/니즈/행동/만족도" }}
  ],
  "pain_points": [
    {{
      "id": "pp_1",
      "title": "페인포인트 제목 (15자 이내)",
      "description": "상세 설명 (1~2문장으로 간결하게)",
      "severity": "high 또는 medium 또는 low",
      "quote": "녹취록 직접 인용 (있을 경우만)"
    }}
  ],
{flows_schema}
}}

=== 규칙 ===
- questions: 핵심 질문만 (중복 제외, 최대 {max_q}개), {clustering_hint}
- pain_points: 불편함·문제점·니즈 (최대 {max_pp}개), description은 1~2문장으로 간결하게, {clustering_hint}
{flows_rule}
- 이 녹취록이 전체의 일부일 수 있음. 보이는 내용만 분석할 것

=== 인터뷰 녹취록 ===
---
{transcript}
---"""


def call_claude(transcript: str, options: dict = None) -> dict:
    """Claude API 단일 호출, 파싱된 dict 반환"""
    payload = json.dumps({
        "model":      MODEL,
        "max_tokens": MAX_OUT,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": build_user_message(transcript, options)}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key":          API_KEY,
            "anthropic-version":  "2023-06-01",
            "content-type":       "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())

    raw = body.get("content", [{}])[0].get("text", "")
    stop = body.get("stop_reason", "")
    print(f"  → stop_reason={stop}, 응답 길이={len(raw)}자")
    return parse_json_robust(raw)


# ──────────────────────────────────────────────
# 청크 분할 & 병합
# ──────────────────────────────────────────────
def split_transcript(text: str, chunk_words: int = CHUNK_WORDS) -> list[str]:
    """녹취록을 chunk_words 단위로 분할 (문장 경계 존중)"""
    words = text.split()
    if len(words) <= chunk_words:
        return [text]

    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_words]
        chunks.append(" ".join(chunk))
        i += chunk_words
    return chunks


def merge_results(parts: list[dict]) -> dict:
    """여러 청크 분석 결과를 하나로 병합 (중복 제거)"""
    if not parts:
        return {"interview_title": "", "questions": [], "pain_points": [], "flows": []}

    merged = {
        "interview_title": parts[0].get("interview_title", ""),
        "questions":   [],
        "pain_points": [],
        "flows":       [],
    }

    seen_q  = set()
    seen_pp = set()

    for i, part in enumerate(parts):
        # questions 병합: 텍스트 앞 20자 기준 중복 제거
        for q in part.get("questions", []):
            key = q.get("text", "")[:20]
            if key not in seen_q:
                seen_q.add(key)
                q["id"] = f"q_{len(merged['questions']) + 1}"
                merged["questions"].append(q)

        # pain_points 병합: title 기준 중복 제거
        for pp in part.get("pain_points", []):
            key = pp.get("title", "")
            if key not in seen_pp:
                seen_pp.add(key)
                pp["id"] = f"pp_{len(merged['pain_points']) + 1}"
                merged["pain_points"].append(pp)

        # flows: 청크별로 id prefix 추가해 병합
        for fl in part.get("flows", []):
            prefix = f"c{i+1}_"
            fl["id"] = prefix + fl.get("id", f"flow_{i}")
            for nd in fl.get("nodes", []):
                nd["id"] = prefix + nd.get("id", "n")
            for eg in fl.get("edges", []):
                eg["id"]     = prefix + eg.get("id", "e")
                eg["source"] = prefix + eg.get("source", "")
                eg["target"] = prefix + eg.get("target", "")
            merged["flows"].append(fl)

    return merged


# ──────────────────────────────────────────────
# 강건한 JSON 파서
# ──────────────────────────────────────────────
def parse_json_robust(text: str) -> dict:
    # 전략 1: 직접 파싱
    try: return json.loads(text.strip())
    except Exception: pass

    # 전략 2: 마크다운 펜스 제거
    stripped = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I).rstrip().rstrip("```").strip()
    try: return json.loads(stripped)
    except Exception: pass

    # 전략 3: {...} 블록 추출
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try: return json.loads(m.group())
        except Exception: pass

    # 전략 4: unquoted key 수정
    if m:
        fixed = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', m.group())
        try: return json.loads(fixed)
        except Exception: pass

    # 전략 5: 잘린 JSON 복구 (max_tokens 초과)
    start = text.find("{")
    if start != -1:
        partial = text[start:]
        closes = {"{": "}", "[": "]"}
        stack, in_str, esc = [], False, False
        for ch in partial:
            if esc:        esc = False; continue
            if ch == "\\" and in_str: esc = True; continue
            if ch == '"':  in_str = not in_str; continue
            if in_str:     continue
            if ch in closes: stack.append(closes[ch])
            elif ch in ("}","]") and stack and stack[-1] == ch: stack.pop()
        if stack:
            recovered = partial.rstrip().rstrip(",") + "".join(reversed(stack))
            try: return json.loads(recovered)
            except Exception: pass

    raise ValueError(f"JSON 파싱 실패. 응답 시작: {text[:100]!r}")


# ──────────────────────────────────────────────
# HTTP 핸들러
# ──────────────────────────────────────────────
class AnalyzerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/interview_analyzer.html"
        super().do_GET()

    def do_POST(self):
        if self.path != "/analyze":
            self.send_error(404)
            return

        if not API_KEY:
            self._respond(500, {"error": "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다."})
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))

        transcript  = body.get("transcript", "")
        source_name = body.get("source_name", "인터뷰")
        options     = body.get("options") or {}

        if not transcript.strip():
            self._respond(400, {"error": "녹취록이 비어있습니다."})
            return

        try:
            chunks = split_transcript(transcript)
            total  = len(chunks)
            print(f"[analyze] 청크 {total}개로 분할 ({len(transcript.split())}단어)")
            print(f"[analyze] 옵션: clustering={options.get('clustering','normal')}, "
                  f"flows={options.get('include_flows', True)}, focus={options.get('focus','balanced')}")

            parts = []
            for idx, chunk in enumerate(chunks):
                print(f"[analyze] 청크 {idx+1}/{total} 분석 중...")
                result = call_claude(chunk, options)
                parts.append(result)

            merged = merge_results(parts)
            merged["schema_version"] = "1.0"
            merged["analyzed_at"]    = __import__("datetime").date.today().isoformat()
            merged["source_file"]    = source_name
            merged["chunk_count"]    = total

            print(f"[analyze] 완료 — 질문 {len(merged['questions'])}개, "
                  f"페인포인트 {len(merged['pain_points'])}개, "
                  f"플로우 {len(merged['flows'])}개")

            self._respond(200, merged)

        except urllib.error.HTTPError as e:
            err = json.loads(e.read()).get("error", {})
            self._respond(e.code, {"error": err.get("message", f"HTTP {e.code}")})
        except Exception as e:
            print(f"[analyze] 오류: {e}")
            self._respond(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        print(f"[server] {fmt % args}")


if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  경고: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   source ~/.zshrc 를 실행한 뒤 다시 시도하세요.")
    else:
        print(f"✓  API 키 로드됨 (길이: {len(API_KEY)}자)")

    # 로컬 IP 확인
    try:
        import socket
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "확인 불가 (ipconfig/ifconfig 로 직접 확인)"

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("0.0.0.0", PORT), AnalyzerHandler)
    print(f"✓  서버 시작 (모든 네트워크 인터페이스)")
    print(f"   내 PC:    http://localhost:{PORT}")
    print(f"   팀원 접속: http://{local_ip}:{PORT}  ← 이 주소를 FigJam 플러그인에 입력")
    print(f"   청크 크기: {CHUNK_WORDS}단어 / 청크")
    print("   종료: Ctrl+C\n")
    server.serve_forever()
