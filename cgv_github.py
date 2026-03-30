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
    """텔레그램 메시지 중 '가장 마지막' 메시지 하나만 정확히 추출"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res["ok"] and res["result"]:
            # 메시지 목록을 시간 역순(최신순)으로 정렬
            valid_commands = []
            for update in res["result"]:
                msg = update.get("message", {})
                text = msg.get("text", "")
                user_id = str(msg.get("from", {}).get("id", ""))
                
                if user_id == CHAT_ID and text.startswith("/set"):
                    valid_commands.append(text)
            
            # 유효한 명령어 중 가장 마지막(최신) 것만 선택
            if valid_commands:
                last_command = valid_commands[-1]
                parts = last_command.split(" ")
                new_date = re.sub(r'[^0-9]', '', parts[1]) if len(parts) >= 2 else TARGET_DATE
                new_title = " ".join(parts[2:]) if len(parts) > 2 else ""
                
                # 확인 메시지 발송
                confirm_msg = f"⚙️ 최신 명령 확인!\n📅 날짜: {new_date}\n🎬 영화: {new_title if new_title else '전체'}\n위 조건으로 지금 즉시 스캔합니다."
                send_telegram(confirm_msg)
                return new_date, new_title
    except Exception as e:
        print(f"명령어 확인 중 오류: {e}")
    
    return TARGET_DATE, MOVIE_TITLE

def check_cgv_online():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 실행 시점에 텔레그램 최신 명령 확인
        current_date, current_title = get_latest_command()

        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={current_date}"
        driver.get(url)
        time.sleep(15) # 충분한 로딩 시간

        page_source = driver.page_source.upper()
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] 검사 중: {current_date} / {current_title}")

        # IMAX 및 영화 제목 체크
        if "IMAX" in page_source:
            # 제목 필터링 (입력값이 있을 때만)
            if not current_title or current_title.upper() in page_source:
                send_telegram(f"🎯 [오픈 감지!] {current_date} {current_title} IMAX 예매가 열렸습니다!")
                return
        
        print("❄️ 아직 조건에 맞는 일정이 없습니다.")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
