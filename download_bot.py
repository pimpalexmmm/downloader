import os
import re
import sys
import json
import signal
import requests
from pyrubi import Client
from pyrubi.types import Message

# ========== دریافت اطلاعات حساب از متغیر محیطی ==========
account_json = os.environ.get("ACCOUNT_JSON")
if not account_json:
    print("❌ متغیر ACCOUNT_JSON تنظیم نشده است.")
    sys.exit(1)

account = json.loads(account_json)
AUTH = account["auth"]
PRIVATE_KEY = account["private_key"]

# ========== تنظیمات دیگر ==========
TIMEOUT = 55 * 60                # 55 دقیقه
DOWNLOAD_DIR = "/tmp/rubika_downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

URL_PATTERN = re.compile(r'https?://[^\s]+')

# ========== ساخت کلاینت ==========
client = Client(auth=AUTH, private=PRIVATE_KEY, platform="android")

@client.on_message()
def handle_message(msg: Message):
    text = msg.text
    if not text:
        return

    urls = URL_PATTERN.findall(text)
    if not urls:
        return

    url = urls[0]
    chat_id = msg.object_guid

    client.send_text(chat_id, "🔽 در حال دانلود فایل... لطفاً صبور باشید.")

    try:
        file_path = download_file(url)
        if hasattr(client, "send_document"):
            client.send_document(chat_id, file_path, caption="✅ فایل شما دانلود شد.")
        elif hasattr(client, "send_file"):
            client.send_file(chat_id, file_path, caption="✅ فایل شما دانلود شد.")
        else:
            client.send_text(chat_id, f"❌ ارسال فایل ممکن نیست. لینک:\n{url}")
        os.remove(file_path)
    except Exception as e:
        client.send_text(chat_id, f"❌ خطا:\n{e}")

def download_file(url):
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()

    filename = None
    cd = resp.headers.get('Content-Disposition')
    if cd:
        fname_match = re.findall('filename="?([^";]+)"?', cd)
        if fname_match:
            filename = fname_match[-1]
    if not filename:
        filename = url.split('/')[-1].split('?')[0] or "downloaded_file"

    file_path = os.path.join(DOWNLOAD_DIR, filename)
    with open(file_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return file_path

def timeout_handler(signum, frame):
    print(f"\n⏰ زمان {TIMEOUT} ثانیه تمام شد. خروج امن...")
    sys.exit(0)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(TIMEOUT)

print("🤖 ربات دانلودر با JSON حساب شروع به کار کرد.")
client.run()
