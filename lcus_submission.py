import json
import time
import getpass
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


LEETCODE_URL = 'https://leetcode.com'
BATCH_SIZE = 20

LANG_EXTENSIONS = {
    'cpp': 'cpp', 'java': 'java', 'python': 'py', 'python3': 'py',
    'c': 'c', 'csharp': 'cs', 'javascript': 'js', 'ruby': 'rb',
    'swift': 'swift', 'golang': 'go', 'scala': 'scala', 'kotlin': 'kt',
    'rust': 'rs', 'mysql': 'sql', 'bash': 'sh'
}

RESET = '\x1b[0m'
BOLD = '\x1b[1m'
GRAY = '\x1b[90m'


def banner(title: str) -> None:
    print(f"{BOLD}▲  {title}{RESET}")


def log(msg: str) -> None:
    print(f"{GRAY}{msg}{RESET}")


def log_timed(msg: str, secs: float) -> None:
    print(f"{GRAY}{msg} [{secs:.1f}s]{RESET}")


@dataclass
class Submission:
    title_slug: str
    lang: str
    timestamp: int
    status: str
    code: str


class LeetCodeScraper:
    def __init__(self) -> None:
        self.username = input('Username: ').strip()
        self.password = getpass.getpass('Password: ')
        log(f'Linked to user: {self.username}')
        self.base_dir = Path(f'lcus_{self.username}')
        self.accepted_dir = self.base_dir / 'Accepted'
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.accepted_dir.mkdir(exist_ok=True)
        self.driver = None
        self.wait = None

    def build_driver(self) -> webdriver.Chrome:
        t0 = time.perf_counter()
        log('Setting up browser…')
        options = webdriver.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        user_data_dir = Path.home() / '.leetcode_chrome'
        options.add_argument(f'--user-data-dir={user_data_dir}')
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'download.prompt_for_download': False,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        }
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(driver, 20)
        log_timed('Browser ready', time.perf_counter() - t0)
        return driver

    def is_logged_in(self) -> bool:
        self.driver.get(LEETCODE_URL)
        time.sleep(1.0)
        return any(c['name'] == 'LEETCODE_SESSION' for c in self.driver.get_cookies())

    def login(self) -> None:
        if not self.driver:
            self.driver = self.build_driver()
        t0 = time.perf_counter()
        log('Checking session…')
        if self.is_logged_in():
            log_timed('Session detected', time.perf_counter() - t0)
            return
        log('Logging in…')
        self.driver.get(f'{LEETCODE_URL}/accounts/login/')
        username_field = self.wait.until(EC.presence_of_element_located((By.ID, 'id_login')))
        password_field = self.driver.find_element(By.ID, 'id_password')
        username_field.clear()
        username_field.send_keys(self.username)
        password_field.clear()
        password_field.send_keys(self.password)
        log('Complete verification in the browser, then press Enter here.')
        input('Continue: ')
        self.wait_until_logged_in()
        log_timed('Logged in', time.perf_counter() - t0)

    def wait_until_logged_in(self, timeout: int = 180) -> None:
        start = time.time()
        while time.time() - start < timeout:
            if any(c['name'] == 'LEETCODE_SESSION' for c in self.driver.get_cookies()):
                return
            time.sleep(1)
        raise RuntimeError('Login was not detected in time.')

    def session_from_driver(self) -> requests.Session:
        log('Syncing session…')
        s = requests.Session()
        for c in self.driver.get_cookies():
            s.cookies.set(c['name'], c['value'])
        s.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Referer': LEETCODE_URL,
            'Accept': 'application/json'
        })
        if 'csrftoken' in s.cookies:
            s.headers['x-csrftoken'] = s.cookies['csrftoken']
        log('Session ready')
        return s

    def fetch_submissions(self, session: requests.Session) -> List[dict]:
        t0 = time.perf_counter()
        log('Fetching submissions…')
        items: List[dict] = []
        last_key = ''
        pages = 0
        while True:
            url = f'{LEETCODE_URL}/api/submissions/?offset=0&limit={BATCH_SIZE}'
            if last_key:
                url += f'&lastkey={last_key}'
            r = session.get(url)
            r.raise_for_status()
            data = r.json()
            chunk = data.get('submissions_dump', []) or []
            if not chunk:
                break
            items.extend(chunk)
            pages += 1
            log(f'page {pages}: +{len(chunk)} (total {len(items)})')
            if not data.get('has_next'):
                break
            last_key = data.get('last_key') or ''
        log_timed(f'Fetched {len(items)} submissions', time.perf_counter() - t0)
        return items

    def save_everything(self, submissions: List[dict]) -> None:
        t0 = time.perf_counter()
        log('Writing files…')
        latest_accepted: Dict[str, dict] = {}
        for raw in submissions:
            slug = raw['title_slug']
            ts = raw['timestamp']
            folder = self.base_dir / slug
            folder.mkdir(exist_ok=True)
            json_path = folder / f'{ts}.json'
            if not json_path.exists():
                with json_path.open('w', encoding='utf-8') as f:
                    json.dump(raw, f, indent=2, ensure_ascii=False)
            if raw.get('status_display') == 'Accepted':
                best = latest_accepted.get(slug)
                if not best or ts > best['timestamp']:
                    latest_accepted[slug] = raw
        for slug, raw in latest_accepted.items():
            lang = raw['lang']
            ext = LANG_EXTENSIONS.get(lang, lang)
            code = raw.get('code', '')
            path = self.accepted_dir / f'{slug}.{ext}'
            with path.open('w', encoding='utf-8') as f:
                f.write(code)
        log_timed(f'Saved {len(latest_accepted)} accepted solutions to {self.accepted_dir}', time.perf_counter() - t0)

    def run(self) -> None:
        start = time.perf_counter()
        self.login()
        session = self.session_from_driver()
        submissions = self.fetch_submissions(session)
        self.save_everything(submissions)
        if self.driver:
            log('Closing browser…')
            self.driver.quit()
        log_timed('Done', time.perf_counter() - start)


if __name__ == '__main__':
    scraper = LeetCodeScraper()
    scraper.run()