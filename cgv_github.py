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
        time.sleep(12) 

        # [검증 1] 실제 선택된 날짜(active) 추출
        # CGV 모바일은 선택된 날짜 li 태그에 'on' 또는 특정 클래스를 붙입니다.
        try:
            active_date_element = driver.find_element(By.CSS_SELECTOR, "li.on[date]")
            actual_date = active_date_element.get_attribute("date")
        except:
            actual_date = "unknown"

        print(f"🔎 요청 날짜: {current_date} | 실제 표시 날짜: {actual_date}")

        # [검증 2] 요청한 날짜와 실제 페이지 날짜가 다르면 즉시 종료
        if current_date != actual_date:
            print(f"⏳ {current_date} 페이지가 아직 생성되지 않았습니다. (현재 {actual_date} 표시 중)")
            return

        # [검증 3] 상영 시간표 데이터가 실제로 있는지 확인
        page_source = driver.page_source
        if "hall_name" not in page_source:
            print(f"❄️ {current_date} : 날짜는 열렸으나 상영 정보가 없습니다.")
            return

        # [검증 4] IMAX 및 제목 매칭
        source_upper = page_source.upper()
        if "IMAX" in source_upper:
            if not current_title or current_title.upper() in source_upper:
                send_telegram(f"🎯 [진짜오픈!] {current_date} {current_title} IMAX 감지!")
                print("🔔 알림 발송!")
            else:
                print(f"❄️ IMAX는 있으나 제목({current_title}) 불일치")
        else:
            print(f"❄️ {current_date} : 일반관만 존재")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
