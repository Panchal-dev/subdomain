import random
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

class RequestHandler:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False

    def _get_headers(self):
        headers = HEADERS.copy()
        headers["user-agent"] = random.choice(USER_AGENTS)
        return headers

    def get(self, url, timeout=10):
        try:
            response = self.session.get(url, timeout=timeout, headers=self._get_headers())
            if response.status_code == 200:
                return response
        except requests.RequestException:
            pass
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()