from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from src.utils.http import RequestHandler

class SubdomainSource(RequestHandler, ABC):
    def __init__(self, name):
        super().__init__()
        self.name = name

    @abstractmethod
    def fetch(self, domain):
        pass

class CrtshSource(SubdomainSource):
    def __init__(self):
        super().__init__("Crt.sh")

    def fetch(self, domain):
        subdomains = set()
        response = self.get(f"https://crt.sh/?q=%25.{domain}&output=json")
        if response and response.headers.get('Content-Type') == 'application/json':
            for entry in response.json():
                subdomains.update(entry['name_value'].splitlines())
        return subdomains

class HackertargetSource(SubdomainSource):
    def __init__(self):
        super().__init__("Hackertarget")

    def fetch(self, domain):
        subdomains = set()
        response = self.get(f"https://api.hackertarget.com/hostsearch/?q={domain}")
        if response and 'text' in response.headers.get('Content-Type', ''):
            subdomains.update([line.split(",")[0] for line in response.text.splitlines()])
        return subdomains

class RapidDnsSource(SubdomainSource):
    def __init__(self):
        super().__init__("RapidDNS")

    def fetch(self, domain):
        subdomains = set()
        response = self.get(f"https://rapiddns.io/subdomain/{domain}?full=1")
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('td'):
                text = link.get_text(strip=True)
                if text.endswith(f".{domain}"):
                    subdomains.add(text)
        return subdomains

def get_sources():
    return [
        CrtshSource(),
        HackertargetSource(),
        RapidDnsSource(),
    ]