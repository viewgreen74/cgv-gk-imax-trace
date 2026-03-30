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
MY_GITHUB_TOKEN = os.environ.get('MY_GITHUB_TOKEN') # PAT 토큰
REPO_NAME = "본인의계정명/저장소명" # 예: "hong-gildong/cgv-trace" 직접 수정 필요!

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})

def get_latest_command():
    """텔레그램 최신 메시지에서 /set 명령어를 읽어옴"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res["ok"] and res["result"]:
            # 가장 최근 메시지부터 역순으로 확인
            for update in reversed(res["result"]):
                text = update.get("message", {}).get("text", "")
                user_id = str(update.get("message", {}).get("from", {}).get("id", ""))
                
                # 본인이 보낸 메시지이고 /set으로 시작하는지 확인
                if user_id == CHAT_ID and text.startswith("/set"):
                    parts = text.split(" ")
                    if len(parts) >= 2:
                        new_date = re.sub(r'[^0-9]', '', parts[1])
                        new_title = " ".join(parts[2:]) if len(parts) > 2 else ""
                        return new_date, new_title
    except: pass
    return None, None

def update_github_secret(name, value):
    """GitHub API를 사용하여 Secret 값을 업데이트 (간이 방식)"""
    # 주의: 실제 GitHub API는 암호화(Sodium)가 필요하여 복잡하므로 
    # 여기서는 '날짜와 제목이 바뀌었음'을 알리는 로그용으로만 출력하거나 
    # 실제 반영을 위해선 수동 업데이트 권장. (API 반영 로직은 별도 라이브러리 필요)
    print(f"🔄 요청된 설정: 날짜({name}), 영화({value})")

def check_cgv_online():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 1. 텔레그램 명령어 체크
        cmd_date, cmd_title = get_latest_command()
        current_date = cmd_date if cmd_date else TARGET_DATE
        current_title = cmd_title if cmd_date else MOVIE_TITLE

        print(f"🚀 추적 대상: {current_date} | 영화: {current_title if current_title else '전체'}")

        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={current_date}"
        driver.get(url)
        time.sleep(12)

        page_source = driver.page_source.upper()
        
        # 2. 결과 검사 로직 (동일)
        if "IMAX" in page_source:
            if not current_title or current_title.upper() in page_source:
                send_telegram(f"🎯 [오픈!] {current_date} {current_title} IMAX 감지!")
                return
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 조건 미충족 (대기 중)")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
