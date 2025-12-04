# -*- coding: utf-8 -*-
"""
yahoo_finance_crawler.py - Yahoo Finance 뉴스 크롤러

Playwright 기반 + 봇 감지 우회
"""

import subprocess
import sys
import platform
import os
import io
import requests
from pathlib import Path

# Windows 콘솔 UTF-8 설정
if platform.system() == "Windows":
    try:
        subprocess.run("chcp 65001", shell=True, capture_output=True, check=True)
    except:
        pass

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"

try:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
except:
    pass

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import time
import random
import logging
import re
from urllib.parse import urljoin, urlparse

# 로깅 설정
logging.getLogger().handlers.clear()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 설정
MAX_RETRIES = 5
MIN_DELAY = 2
MAX_DELAY = 4
BASE_URL = "https://finance.yahoo.com/quote/"

# Lambda 환경 감지
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
TEMP_DIR = "/tmp" if IS_LAMBDA else "temp_images"

if not IS_LAMBDA:
    Path(TEMP_DIR).mkdir(exist_ok=True)
    logger.info(f"임시 이미지 저장 경로: {os.path.abspath(TEMP_DIR)}")


class YahooFinanceCrawler:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    def parse_time_ago(self, time_str):
        """시간 문자열을 분 단위로 변환 (예: '41m ago' → 41, '2h ago' → 120, '1d ago' → 1440)"""
        try:
            # 숫자와 단위 추출
            match = re.search(r"(\d+)\s*([mhd])", time_str.lower())
            if not match:
                return float("inf")  # 파싱 실패시 가장 오래된 것으로 처리

            value = int(match.group(1))
            unit = match.group(2)

            if unit == "m":  # minutes
                return value
            elif unit == "h":  # hours
                return value * 60
            elif unit == "d":  # days
                return value * 60 * 24
            else:
                return float("inf")
        except Exception as e:
            logger.debug(f"시간 파싱 오류: {time_str} - {e}")
            return float("inf")

    def __enter__(self):
        # Stealth 모듈 체크
        try:
            from playwright_stealth import stealth_sync

            self.use_stealth = True
            logger.info("✓ playwright-stealth 로드 성공")
        except ImportError:
            self.use_stealth = False
            logger.warning("⚠ playwright-stealth 없음. 기본 우회만 사용")

        self.playwright = sync_playwright().start()

        # 브라우저 실행
        self.browser = self.playwright.chromium.launch(
            headless=False,  # 디버깅용 (배포시 True로 변경)
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        # 브라우저 컨텍스트 설정
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )

        # Stealth 모드 적용
        if self.use_stealth:
            from playwright_stealth import stealth_sync

            page = self.context.new_page()
            stealth_sync(page)
            page.close()
            logger.info("✓ Stealth 모드 활성화")

        # 봇 감지 우회 스크립트
        self.context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            Object.defineProperties(navigator, {
                plugins: { get: () => [1, 2, 3, 4, 5] },
                languages: { get: () => ['en-US', 'en'] },
                platform: { get: () => 'Win32' },
                hardwareConcurrency: { get: () => 8 },
                deviceMemory: { get: () => 8 }
            });
        """
        )

        logger.info("✓ 브라우저 초기화 완료")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def close_popup_if_exists(self, page):
        """Yahoo Finance 팝업/배너 닫기"""
        try:
            # 쿠키 동의 배너
            cookie_selectors = [
                'button[name="agree"]',
                '[data-testid="consent-accept-all"]',
                ".consent-overlay button.accept",
                'button:has-text("Accept all")',
                'button:has-text("Accept")',
            ]

            for selector in cookie_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.click(selector, timeout=3000)
                        logger.info("✓ 쿠키 동의 클릭")
                        time.sleep(1)
                        return True
                except:
                    continue

            # 일반 모달 닫기
            close_selectors = [
                'button[aria-label="Close"]',
                'button[aria-label*="close" i]',
                '[data-testid="close-button"]',
                ".modal-close",
                "button.close",
            ]

            for selector in close_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.click(selector, timeout=2000)
                        logger.info("✓ 모달 닫기 클릭")
                        time.sleep(1)
                        return True
                except:
                    continue

            # ESC 키
            try:
                page.keyboard.press("Escape")
                time.sleep(0.5)
            except:
                pass

            return False

        except Exception as e:
            logger.debug(f"팝업 처리 오류: {e}")
            return False

    def simulate_human_behavior(self, page):
        """사람처럼 행동 시뮬레이션"""
        try:
            time.sleep(random.uniform(1.5, 3))

            # 마우스 이동
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            time.sleep(random.uniform(0.3, 0.8))

            # 스크롤 (뉴스 더 로드하기 위해)
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(300, 600)
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                time.sleep(random.uniform(0.5, 1.2))

            # 맨 위로
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            logger.debug(f"행동 시뮬레이션 오류: {e}")

    def download_image(self, image_url, article_url, ticker, image_index=1):
        """이미지 다운로드"""
        try:
            # 파일명 생성
            parsed = urlparse(article_url)
            article_id = parsed.path.split("/")[-1][:30] or f"article_{image_index}"

            ext = image_url.split(".")[-1].split("?")[0]
            if ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
                ext = "jpg"

            filename = f"{ticker}_{article_id}_{image_index}.{ext}"
            filepath = os.path.join(TEMP_DIR, filename)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.yahoo.com/",
            }

            response = requests.get(image_url, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info(f"✓ 이미지 저장: {filename}")
                return filepath
            return None

        except Exception as e:
            logger.error(f"이미지 다운로드 오류: {e}")
            return None

    def extract_images(self, soup, article_url, ticker):
        """기사 이미지 추출"""
        images = []
        image_counter = 1
        seen_urls = set()

        # 메인 이미지
        main_selectors = [
            'img[data-testid="lead-image"]',
            "article img",
            ".caas-img-container img",
            ".caas-body img",
        ]

        for selector in main_selectors:
            for img in soup.select(selector):
                image_url = img.get("src") or img.get("data-src")
                if not image_url or image_url in seen_urls:
                    continue

                # 작은 아이콘 제외
                if "icon" in image_url.lower() or "logo" in image_url.lower():
                    continue
                if "avatar" in image_url.lower():
                    continue

                seen_urls.add(image_url)

                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                elif not image_url.startswith("http"):
                    image_url = urljoin("https://finance.yahoo.com", image_url)

                filepath = self.download_image(
                    image_url, article_url, ticker, image_counter
                )
                if filepath:
                    images.append(
                        {
                            "url": image_url,
                            "filepath": filepath,
                            "alt": img.get("alt", ""),
                            "type": "main" if image_counter == 1 else "content",
                        }
                    )
                    image_counter += 1

        return images

    def fetch_url(self, page, url):
        """URL 가져오기"""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📄 [{attempt}/{MAX_RETRIES}] 로딩: {url}")

                if attempt > 1:
                    wait_time = random.uniform(5, 10) * attempt
                    logger.info(f"⏳ {wait_time:.1f}초 대기...")
                    time.sleep(wait_time)

                # 페이지 로드
                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)

                if response:
                    logger.info(f"상태 코드: {response.status}")

                # 로딩 대기
                time.sleep(random.uniform(3, 5))

                # 팝업 처리
                self.close_popup_if_exists(page)

                # 사람처럼 행동
                self.simulate_human_behavior(page)

                html = page.content()

                # 검증
                if len(html) < 3000:
                    logger.warning(f"⚠ HTML 너무 짧음: {len(html)} bytes")
                    time.sleep(5 * attempt)
                    continue

                logger.info(f"✓ 성공 ({len(html):,} bytes)")
                return html

            except PlaywrightTimeout:
                logger.error(f"⏱ 타임아웃 ({attempt}/{MAX_RETRIES})")
                time.sleep(10 * attempt)
            except Exception as e:
                logger.error(f"❌ 오류 ({attempt}/{MAX_RETRIES}): {e}")
                time.sleep(8 * attempt)

        logger.error(f"❌ 모든 시도 실패: {url}")
        return None

    def extract_article_body(self, soup):
        """기사 본문 추출"""
        # Yahoo Finance 기사 본문 셀렉터
        body_selectors = [
            ".caas-body",
            '[data-testid="article-body"]',
            "article .body",
            ".article-body",
        ]

        for selector in body_selectors:
            body_elem = soup.select_one(selector)
            if body_elem:
                # 스크립트/스타일 제거
                for tag in body_elem(["script", "style", "aside", "nav"]):
                    tag.decompose()
                text = body_elem.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

        # fallback: 가장 긴 텍스트 블록 찾기
        candidates = soup.find_all(["article", "main", "div"])
        max_text = ""
        for c in candidates:
            for tag in c(["script", "style"]):
                tag.decompose()
            text = c.get_text(separator="\n", strip=True)
            if len(text) > len(max_text):
                max_text = text
        return max_text

    def extract_news_links(self, soup, ticker, max_articles=10):
        """뉴스 목록에서 기사 링크 추출 (최신순 정렬)"""
        news_links = []
        seen_urls = set()

        # 기사 컨테이너 찾기: li.stream-item.story-item
        article_containers = soup.select("li.stream-item.story-item")
        logger.info(f"🔍 기사 컨테이너 {len(article_containers)}개 발견")

        for container in article_containers:
            # 링크 찾기 (titles 클래스가 있는 a 태그)
            a_tag = container.select_one('a.titles, a[class*="titles"]')
            if not a_tag:
                continue

            href = a_tag.get("href", "")

            # 제목 찾기 (h3.clamp)
            h3_tag = a_tag.select_one("h3.clamp")
            title = (
                h3_tag.get_text(strip=True) if h3_tag else a_tag.get_text(strip=True)
            )

            if not href or not title:
                continue

            # 전체 URL 생성
            if href.startswith("/"):
                full_url = f"https://finance.yahoo.com{href}"
            elif not href.startswith("http"):
                full_url = urljoin("https://finance.yahoo.com", href)
            else:
                full_url = href

            # 중복 체크
            if full_url in seen_urls:
                continue

            # 비디오/광고 제외
            if "/video/" in full_url:
                continue
            if "ad.doubleclick" in full_url:
                continue

            # 시간 정보 추출 (.publishing)
            time_str = ""
            time_minutes = float("inf")

            time_elem = container.select_one('.publishing, div[class*="publishing"]')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # "Reuters Videos • 36m ago" 에서 시간 부분만 추출
                time_match = re.search(r"(\d+)\s*([mhd])\s*ago", time_text.lower())
                if time_match:
                    time_str = f"{time_match.group(1)}{time_match.group(2)} ago"
                    time_minutes = self.parse_time_ago(time_str)

            # 시간 정보 없으면 제외
            if not time_str:
                logger.debug(f"시간 정보 없음, 제외: {title[:40]}...")
                continue

            seen_urls.add(full_url)
            news_links.append(
                {
                    "title": title,
                    "url": full_url,
                    "time_str": time_str,
                    "time_minutes": time_minutes,
                }
            )

        # 시간 기준 정렬 (최신순 = 분이 작은 순)
        news_links.sort(key=lambda x: x["time_minutes"])

        # 상위 max_articles개만 선택
        news_links = news_links[:max_articles]

        # 로그 출력
        for idx, news in enumerate(news_links, start=1):
            logger.info(f"[{idx:2d}] 📝 {news['title']}")
            logger.info(f"      🔗 {news['url']}")
            logger.info(f"      ⏰ {news['time_str']}")

        logger.info(f"\n📰 최신순 정렬 후 상위 {len(news_links)}개 기사 링크 추출")
        return news_links

    def crawl_company(self, ticker, count):
        """회사(티커) 뉴스 수집"""
        results = []
        seen_titles = set()

        news_page_url = f"{BASE_URL}{ticker}/news/"
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 {ticker} 크롤링 시작")
        logger.info(f"🔗 {news_page_url}")
        logger.info(f"{'='*70}\n")

        page = self.context.new_page()

        try:
            # 뉴스 목록 페이지 가져오기
            html = self.fetch_url(page, news_page_url)
            if html is None:
                return results

            soup = BeautifulSoup(html, "lxml")

            # 기사 링크 추출
            news_links = self.extract_news_links(soup, ticker, max_articles=10)

            logger.info("=" * 70)

            if not news_links:
                logger.warning(f"⚠ 기사 링크를 찾지 못함. HTML 구조 확인 필요")
                # 디버깅용 HTML 저장
                debug_path = os.path.join(TEMP_DIR, f"{ticker}_debug.html")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(html)
                logger.info(f"디버깅용 HTML 저장: {debug_path}")
                return results

            # 각 기사 크롤링
            for idx, news_item in enumerate(news_links[:count], start=1):
                article_url = news_item["url"]

                logger.info(f"\n{'='*70}")
                logger.info(f"📄 기사 [{idx}/{count}] 크롤링 중...")
                logger.info(f"🔗 {article_url}")
                logger.info(f"{'='*70}")

                # 기사 페이지 가져오기
                article_html = self.fetch_url(page, article_url)
                if article_html is None:
                    logger.error(f"❌ 기사 [{idx}] 가져오기 실패")
                    continue

                article_soup = BeautifulSoup(article_html, "lxml")

                # 제목 추출 (Yahoo Finance cover-headline 우선)
                title_selectors = [
                    ".cover-headline h1.cover-title",  # Yahoo Finance 메인 제목
                    "h1.cover-title",
                    'h1[data-testid="article-title"]',
                    "header h1",
                    "article h1",
                    "h1",
                ]

                title = news_item["title"]
                for selector in title_selectors:
                    title_tag = article_soup.select_one(selector)
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        break

                # 중복 제목 체크
                if title in seen_titles:
                    logger.warning(f"⚠ 중복 제목: {title}")
                    continue
                seen_titles.add(title)

                # 본문 추출
                body = self.extract_article_body(article_soup)

                # 이미지 추출
                images = self.extract_images(article_soup, article_url, ticker)

                logger.info(f"✅ 기사 수집 완료!")
                logger.info(f"   📌 제목: {title}")
                logger.info(f"   🔗 링크: {article_url}")
                logger.info(f"   ⏰ 게시: {news_item.get('time_str', '시간 없음')}")
                logger.info(
                    f"   📝 본문 미리보기: {body[:100].replace(chr(10), ' ')}..."
                )
                logger.info(f"   📝 본문 길이: {len(body):,}자")
                logger.info(f"   🖼️  이미지: {len(images)}개")

                results.append(
                    {
                        "ticker": ticker,
                        "title": title,
                        "body": body,
                        "url": article_url,
                        "images": images,
                        "time_ago": news_item.get("time_str", ""),
                    }
                )

                # 요청 간 딜레이
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        finally:
            page.close()

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ {ticker} 크롤링 완료: 총 {len(results)}개 기사")
        logger.info(f"{'='*70}\n")

        return results


def crawl_all(company_list):
    """전체 크롤링 실행"""
    # 입력 형식 표준화
    standardized_list = []
    for item in company_list:
        if isinstance(item, dict):
            standardized_list.append(item)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            standardized_list.append({"name": item[0], "count": item[1]})

    all_results = []

    with YahooFinanceCrawler() as crawler:
        for comp in standardized_list:
            ticker = comp["name"]
            count = comp["count"]
            comp_results = crawler.crawl_company(ticker, count)
            all_results.extend(comp_results)

    return all_results
