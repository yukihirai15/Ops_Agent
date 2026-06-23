"""
Dummy API service that simulates high error rates.
Exposes /metrics for Prometheus scraping.
"""
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

METRICS = {
    "http_requests_total_ok": 10,
    "http_requests_total_err": 0,
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # suppress access logs

    def do_GET(self):
        if self.path == "/metrics":
            # Simulate ~60% error rate
            METRICS["http_requests_total_ok"] += random.randint(1, 3)
            METRICS["http_requests_total_err"] += random.randint(4, 8)

            body = f"""# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{{instance="api:8000",status="200",job="api"}} {METRICS["http_requests_total_ok"]}
http_requests_total{{instance="api:8000",status="500",job="api"}} {METRICS["http_requests_total_err"]}
http_requests_total{{instance="api:8000",status="503",job="api"}} {random.randint(2,10)}
# HELP up Service up status
# TYPE up gauge
up{{instance="api:8000",job="api"}} 0
""".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/health":
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"Service Degraded")

        else:
            # Simulate 5xx on all other endpoints
            if random.random() < 0.7:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Internal Server Error: DB connection pool exhausted")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")

if __name__ == "__main__":
    print("Error service running on :8001")
    HTTPServer(("0.0.0.0", 8001), Handler).serve_forever()
