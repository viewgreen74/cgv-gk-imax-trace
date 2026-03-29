import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 환경 변수 로드 (GitHub Secrets에서 설정할 값들)
TARGET_DATE = os.environ.get('TARGET_DATE')
MOVIE_TITLE = os.environ.get('MOVIE_TITLE', '') # 선택 사항
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

def check_cgv_online():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={TARGET_DATE}"
        driver.get(url)
        time.sleep(10) # 서버 환경에 맞춰 넉넉히 대기 [cite: 66]

        page_source = driver.page_source
        formatted_date = f"{TARGET_DATE[:4]}.{TARGET_DATE[4:6]}.{TARGET_DATE[6:]}"
        
        # 날짜 일치 확인
        if formatted_date not in page_source and TARGET_DATE not in page_source:
            print(f"[{datetime.now()}] ⏳ {TARGET_DATE} 페이지 미오픈")
            return

        # IMAX 및 영화 제목 체크
        source_upper = page_source.upper()
        if "IMAX" in source_upper:
            if not MOVIE_TITLE or MOVIE_TITLE.upper() in source_upper:
                msg = f"🎯 [CGV 광교 IMAX 오픈!] \n날짜: {TARGET_DATE} \n영화: {MOVIE_TITLE if MOVIE_TITLE else 'IMAX 전체'}"
                send_telegram(msg)
                print("🔔 알림 발송 완료!")
            else:
                print(f"[{datetime.now()}] IMAX는 열렸으나 {MOVIE_TITLE} 아님")
        else:
            print(f"[{datetime.now()}] {TARGET_DATE} IMAX 일정 없음")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
