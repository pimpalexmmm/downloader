import os
import re
import sys
import signal
import requests
from pyrubi import Client
from pyrubi.types import Message

# ========== تنظیمات ==========
SESSION_NAME = "tabchi_session"           # نام فایل نشست (بدون پسوند)
TIMEOUT = 55 * 60                # 55 دقیقه؛ اجرا پیش از اتمام ۶۰ دقیقه cron
DOWNLOAD_DIR = "/tmp/rubika_downloads"
# ==============================

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# الگوی ساده برای یافتن لینک مستقیم
URL_PATTERN = re.compile(r'https?://[^\s]+')

# بارگذاری نشست (فایل باید در کنار اسکریپت باشد)
client = Client(session=SESSION_NAME)

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

    # اطلاع‌رسانی اولیه
    client.send_text(chat_id, "🔽 در حال دانلود فایل... لطفاً صبور باشید.")

    try:
        file_path = download_file(url)
        # ارسال فایل به همان چت
        if hasattr(client, "send_document"):
            client.send_document(chat_id, file_path, caption="✅ فایل شما دانلود شد.")
        elif hasattr(client, "send_file"):
            client.send_file(chat_id, file_path, caption="✅ فایل شما دانلود شد.")
        else:
            # اگر متدی پیدا نشد، فقط لینک را دوباره می‌فرستیم
            client.send_text(chat_id, f"❌ ارسال فایل پشتیبانی نمی‌شود. لینک:\n{url}")
        os.remove(file_path)   # پاکسازی فایل موقت
    except Exception as e:
        client.send_text(chat_id, f"❌ خطا:\n{e}")

def download_file(url):
    """دانلود فایل از لینک مستقیم و برگرداندن مسیر ذخیره"""
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()

    # استخراج نام فایل از Content-Disposition یا URL
    filename = None
    cd = resp.headers.get('Content-Disposition')
    if cd:
        fname_match = re.findall('filename="?([^";]+)"?', cd)
        if fname_match:
            filename = fname_match[-1]
    if not filename:
        filename = url.split('/')[-1].split('?')[0]
        if not filename:
            filename = "downloaded_file"

    file_path = os.path.join(DOWNLOAD_DIR, filename)
    with open(file_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return file_path

# ---------- تایمر برای خروج خودکار (مخصوص GitHub Actions) ----------
def timeout_handler(signum, frame):
    print(f"\n⏰ زمان {TIMEOUT} ثانیه تمام شد. خروج امن...")
    sys.exit(0)

# SIGALRM فقط در لینوکس/مک موجود است (در Actions اوبونتو به‌خوبی کار می‌کند)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(TIMEOUT)

print(f"🤖 ربات دانلودر با نشست '{SESSION_NAME}' شروع به کار کرد.")
print(f"🕒 اجرای خودکار تا {TIMEOUT//60} دقیقه دیگر ادامه خواهد داشت.")
client.run()
