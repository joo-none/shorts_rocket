import requests
from bs4 import BeautifulSoup
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dataclasses import dataclass
from typing import List, Optional
import json
import logging
from datetime import datetime


@dataclass
class NewsArticle:
    title: str
    content: str
    url: str
    published_date: str
    image_url: Optional[str] = None
    summary: Optional[str] = None


class InvestingCrawler:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.setup_headers()

    def setup_driver(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.driver = webdriver.Chrome(options=chrome_options)

    def setup_headers(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def get_latest_news(self, limit=10) -> List[NewsArticle]:
        """investing.com에서 최신 뉴스를 크롤링"""
        try:
            url = "https://www.investing.com/news/latest-news"
            self.driver.get(url)

            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "largeTitle"))
            )

            articles = []
            article_elements = self.driver.find_elements(By.CSS_SELECTOR, "article")[
                :limit
            ]

            for element in article_elements:
                try:
                    article = self._extract_article_data(element)
                    if article:
                        articles.append(article)
                        time.sleep(random.uniform(1, 3))  # 차단 방지
                except Exception as e:
                    logging.error(f"Article extraction error: {e}")
                    continue

            return articles

        except Exception as e:
            logging.error(f"Crawling error: {e}")
            return []

    def _extract_article_data(self, element) -> Optional[NewsArticle]:
        """개별 기사 데이터 추출"""
        try:
            title_elem = element.find_element(By.CSS_SELECTOR, "a.title")
            title = title_elem.text.strip()
            url = title_elem.get_attribute("href")

            # 기사 상세 페이지에서 내용 크롤링
            full_content = self._get_article_content(url)

            # 이미지 URL 추출
            try:
                img_elem = element.find_element(By.CSS_SELECTOR, "img")
                image_url = img_elem.get_attribute("src")
            except:
                image_url = None

            # 발행 날짜 추출
            try:
                date_elem = element.find_element(By.CSS_SELECTOR, ".date")
                published_date = date_elem.text.strip()
            except:
                published_date = datetime.now().strftime("%Y-%m-%d %H:%M")

            return NewsArticle(
                title=title,
                content=full_content,
                url=url,
                published_date=published_date,
                image_url=image_url,
            )

        except Exception as e:
            logging.error(f"Article data extraction error: {e}")
            return None

    def _get_article_content(self, url) -> str:
        """기사 상세 내용 크롤링"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "articlePage"))
            )

            content_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".articlePage p"
            )
            content = "\n".join(
                [elem.text for elem in content_elements if elem.text.strip()]
            )

            return content

        except Exception as e:
            logging.error(f"Content extraction error: {e}")
            return "Content extraction failed"

    def save_articles(self, articles: List[NewsArticle], filename: str):
        """크롤링한 기사를 JSON 파일로 저장"""
        data = []
        for article in articles:
            data.append(
                {
                    "title": article.title,
                    "content": article.content,
                    "url": article.url,
                    "published_date": article.published_date,
                    "image_url": article.image_url,
                    "summary": article.summary,
                    "crawled_at": datetime.now().isoformat(),
                }
            )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logging.info(f"Saved {len(articles)} articles to {filename}")

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    crawler = InvestingCrawler()
    try:
        articles = crawler.get_latest_news(limit=5)
        crawler.save_articles(articles, "data/crawled/latest_news.json")
        print(f"Successfully crawled {len(articles)} articles")
    finally:
        crawler.close()
