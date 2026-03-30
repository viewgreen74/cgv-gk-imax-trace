import os
import time
import requests
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 환경 변수 로드 ---
TARGET_DATE = os.environ.get('TARGET_DATE')
MOVIE_TITLE = os.environ.get('MOVIE_TITLE', '')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})

def get_latest_command():
    """텔레그램에서 가장 최신 /set 명령어 하나만 추출"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res["ok"] and res["result"]:
            valid_commands = []
            for update in res["result"]:
                msg = update.get("message", {})
                text = msg.get("text", "")
                user_id = str(msg.get("from", {}).get("id", ""))
                if user_id == CHAT_ID and text.startswith("/set"):
                    valid_commands.append(text)
            
            if valid_commands:
                last_command = valid_commands[-1]
                parts = last_command.split(" ")
                new_date = re.sub(r'[^0-9]', '', parts[1]) if len(parts) >= 2 else TARGET_DATE
                new_title = " ".join(parts[2:]) if len(parts) > 2 else ""
                
                send_telegram(f"⚙️ 명령 확인: {new_date} / {new_title if new_title else '전체'}\n데이터 검증을 시작합니다.")
                return new_date, new_title
    except: pass
    return TARGET_DATE, MOVIE_TITLE

def check_cgv_online():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        current_date, current_title = get_latest_command()
        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={current_date}"
        driver.get(url)
        time.sleep(15) # 로딩 대기

        # [핵심 검증] 현재 페이지 소스에 내가 입력한 날짜가 실제로 존재하는지 확인
        # CGV는 페이지 상단에 YYYY.MM.DD 형식으로 날짜를 표시합니다.
        formatted_date = f"{current_date[:4]}.{current_date[4:6]}.{current_date[6:]}"
        page_source = driver.page_source
        
        # 1. 날짜 불일치 시 (자동 이동된 경우) 알람 무시
        if formatted_date not in page_source:
            print(f"[{datetime.now()}] ⏳ 대기: {current_date} 페이지가 아직 생성되지 않음 (다른 날짜로 이동됨)")
            return

        # 2. 날짜가 일치한다면 IMAX 키워드와 영화 제목 검사
        source_upper = page_source.upper()
        if "IMAX" in source_upper:
            # 영화 제목 필터 적용
            if not current_title or current_title.upper() in source_upper:
                # '상영시간표' 혹은 'hall_name'이 있어야 진짜 시간표가 로드된 것임
                if "HALL_NAME" in source_upper or "상영시간표" in page_source:
                    send_telegram(f"🎯 [진짜 오픈!] {current_date} {current_title} IMAX 예매가 가능합니다!")
                    return
        
        print(f"[{datetime.now()}] ❄️ {current_date} : 페이지는 열렸으나 IMAX 배정 전입니다.")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
