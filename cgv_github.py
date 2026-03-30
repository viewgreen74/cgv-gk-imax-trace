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
    """텔레그램 메시지를 읽어와서 설정을 업데이트함"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res["ok"] and res["result"]:
            # 가장 최근 메시지 확인
            last_update = res["result"][-1]
            text = last_update.get("message", {}).get("text", "")
            user_id = str(last_update.get("message", {}).get("from", {}).get("id", ""))
            msg_id = last_update.get("message", {}).get("message_id")

            # 중복 실행 방지를 위해 최근 10분 내 메시지만 처리 (GitHub 실행 주기 기준)
            if user_id == CHAT_ID and text.startswith("/set"):
                parts = text.split(" ")
                new_date = re.sub(r'[^0-9]', '', parts[1]) if len(parts) >= 2 else TARGET_DATE
                new_title = " ".join(parts[2:]) if len(parts) > 2 else ""
                
                # [중요] 사용자에게 변경 확인 메시지 발송
                confirm_msg = f"⚙️ 설정 변경 완료!\n📅 날짜: {new_date}\n🎬 영화: {new_title if new_title else '전체'}\n위 조건으로 추적을 시작합니다."
                send_telegram(confirm_msg)
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
        # 1. 실행 시점에 텔레그램 명령어가 있는지 확인 후 적용
        current_date, current_title = get_latest_command()

        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={current_date}"
        driver.get(url)
        time.sleep(12)

        page_source = driver.page_source.upper()
        
        # 2. 날짜 확인 로그 출력 (GitHub Actions 로그용)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 추적 중: {current_date} / {current_title}")

        # 3. IMAX 및 영화 제목 체크
        if "IMAX" in page_source:
            if not current_title or current_title.upper() in page_source:
                send_telegram(f"🎯 [오픈 감지!] {current_date} {current_title} IMAX 예매가 가능합니다!")
                return
        
        print("❄️ 조건 미충족 (아직 오픈되지 않음)")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
