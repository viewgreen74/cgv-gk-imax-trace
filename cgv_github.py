import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

TARGET_DATE = os.environ.get('TARGET_DATE')
MOVIE_TITLE = os.environ.get('MOVIE_TITLE', '')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})

def check_cgv_online():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={TARGET_DATE}"
        driver.get(url)
        time.sleep(12) # 온라인 서버 속도를 고려하여 넉넉히 대기

        # [1단계] 날짜 검증 (가장 가까운 날짜로 리다이렉트 되었는지 확인)
        current_url = driver.current_url
        if TARGET_DATE not in current_url and "playDate=" in current_url:
            print(f"[{datetime.now()}] ⏳ {TARGET_DATE} 페이지가 아직 활성화되지 않음 (자동 이동됨)")
            return

        # [2단계] 상영관 리스트 전체 스캔 (정밀 검사)
        halls = driver.find_elements(By.CLASS_NAME, "hall_name") # 상영관 이름 클래스
        all_content = driver.page_source.upper()
        
        imax_found = False
        found_movie = "확인 불가"

        # 'IMAX' 텍스트 혹은 특정 태그 확인
        if "IMAX" in all_content:
            # 영화 제목 필터가 있는 경우
            if MOVIE_TITLE:
                if MOVIE_TITLE.upper() in all_content:
                    imax_found = True
                    found_movie = MOVIE_TITLE
            else:
                imax_found = True
                found_movie = "IMAX 상영관"

        if imax_found:
            msg = f"🎯 [오픈 확인!] CGV 광교\n날짜: {TARGET_DATE}\n영화: {found_movie}\n지금 바로 예매하세요!"
            send_telegram(msg)
            print(f"🔔 알림 발송 완료: {found_movie}")
        else:
            print(f"[{datetime.now()}] ❄️ {TARGET_DATE} : IMAX 일정을 찾을 수 없습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
