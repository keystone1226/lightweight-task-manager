"""
Interview Analyzer - Local Proxy Server
환경변수 ANTHROPIC_API_KEY를 읽어 Anthropic API를 프록시합니다.
"""
import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT = 5500


class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # "/" → interview_analyzer.html 서빙
        if self.path in ("/", ""):
            self.path = "/interview_analyzer.html"
        super().do_GET()

    def do_POST(self):
        if self.path != "/proxy":
            self.send_error(404)
            return

        if not API_KEY:
            self._respond(500, {"error": {"message": "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다."}})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "x-api-key": API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
            self._raw_respond(200, data)

        except urllib.error.HTTPError as e:
            data = e.read()
            self._raw_respond(e.code, data)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, code, obj):
        self._raw_respond(code, json.dumps(obj).encode())

    def _raw_respond(self, code, data):
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
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

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("localhost", PORT), ProxyHandler)
    print(f"✓  서버 시작: http://localhost:{PORT}")
    print("   종료: Ctrl+C\n")
    server.serve_forever()
