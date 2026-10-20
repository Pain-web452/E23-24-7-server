import os
import time
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# Server kab start hua uski timing note karne ke liye global variable
SERVER_START_TIME = datetime.now()
TOTAL_SENT_COUNTER = 0

# ----------------------------------------------------
# 1. CLOUD CONTAINER COMPATIBLE DRIVER INITIALIZER
# ----------------------------------------------------
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")

    chrome_bin = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
    chromedriver_bin = "/opt/render/project/.render/chromedriver/chromedriver"
    
    if os.path.exists(chrome_bin):
        chrome_options.binary_location = chrome_bin
    
    if os.path.exists(chromedriver_bin):
        service = Service(executable_path=chromedriver_bin)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
        
    return driver

# ----------------------------------------------------
# 2. STATUS API FOR LIVE STATS (UPTIME & COUNTER)
# ----------------------------------------------------
@app.route('/api/stats', methods=['GET'])
def get_stats():
    global TOTAL_SENT_COUNTER, SERVER_START_TIME
    
    # Live server uptime calculate karna
    uptime_delta = datetime.now() - SERVER_START_TIME
    days = uptime_delta.days
    hours = uptime_delta.seconds // 3600
    minutes = (uptime_delta.seconds % 3600) // 60
    
    uptime_str = f"{days} Din, {hours} Ghante, {minutes} Minute"
    
    return jsonify({
        "uptime": uptime_str,
        "total_sent": TOTAL_SENT_COUNTER
    })

# ----------------------------------------------------
# 3. WEB USER INTERFACE ROUTING
# ----------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# ----------------------------------------------------
# 4. MESSENGER INBOX AUTOMATION SYSTEM CORE
# ----------------------------------------------------
@app.route('/start-automation', methods=['POST'])
def start_automation():
    global TOTAL_SENT_COUNTER
    
    chat_id = request.form.get('chat_id')
    name_prefix = request.form.get('name_prefix', '').strip()
    delay = int(request.form.get('delay', 30))
    cookies_raw = request.form.get('cookies', '').strip()
    messages_text = request.form.get('messages', '')
    
    messages_list = [msg.strip() for msg in messages_text.split('\n') if msg.strip()]
    
    if not chat_id or not messages_list:
        return jsonify({"status": "error", "message": "Chat ID aur Messages likhna compulsory hai!"})
        
    driver = None
    try:
        driver = get_driver()
        driver.get("https://facebook.com")
        time.sleep(2)
        
        try:
            cookies_list = json.loads(cookies_raw)
            for cookie in cookies_list:
                fixed_cookie = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': '.facebook.com'
                }
                driver.add_cookie(fixed_cookie)
            print("Cookies successfully injected!")
        except Exception as cookie_err:
            print(f"Cookie parse warning: {str(cookie_err)}.")
            
        target_chat_url = f"https://facebook.com/messages/read/?tid={chat_id}"
        driver.get(target_chat_url)
        time.sleep(4)
        
        current_session_sent = 0
        for index, raw_msg in enumerate(messages_list):
            final_message = f"{name_prefix} {raw_msg}" if name_prefix else raw_msg
            
            try:
                message_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body textarea"))
                )
                message_box.send_keys(final_message)
                time.sleep(1)
                
                send_button = driver.find_element(By.NAME, "send")
                send_button.click()
                
                # Global counter aur live updates increase karein
                TOTAL_SENT_COUNTER += 1
                current_session_sent += 1
                print(f"[{index + 1}] Sent successfully to IB: {final_message}")
            except Exception as elem_err:
                if driver:
                    driver.quit()
                return jsonify({"status": "error", "message": f"Locator Crash: Element nahi mila."})
                
            time.sleep(delay)
            
        driver.quit()
        return jsonify({"status": "success", "message": f"🎉 Is session me total {current_session_sent} messages successfully safely transfer ho gaye hain!"})
        
    except Exception as general_err:
        if driver:
            driver.quit()
        return jsonify({"status": "error", "message": f"System crash: {str(general_err)}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
        
