import requests
import time
import os
import re
import json
import sys
import signal

# ==================== تنظیمات ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")   # از Secret خوانده می‌شود
if not BOT_TOKEN:
    print("❌ BOT_TOKEN تنظیم نشده است.")
    sys.exit(1)

BASE_URL = f"https://botapi.rubika.ir/v3/{BOT_TOKEN}"
DOWNLOAD_DIR = "/tmp/rubika_downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# حداکثر زمان اجرا (55 دقیقه برای ماندن در محدوده 60 دقیقه‌ای Actions)
TIMEOUT = 55 * 60  # ثانیه
# حداکثر تعداد پیام پردازشی در هر اجرا (برای جلوگیری از حلقه بی‌نهایت)
MAX_MESSAGES_PER_RUN = 10

# الگوی تشخیص لینک مستقیم
URL_PATTERN = re.compile(r'https?://[^\s]+')
# =================================================

def get_updates(offset_id=None, limit=10):
    """دریافت آپدیت‌های جدید از سرور روبیکا (طبق مستندات رسمی)"""
    url = f"{BASE_URL}/getUpdates"
    payload = {"limit": limit}
    if offset_id is not None:
        payload["offset_id"] = offset_id
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"خطا در getUpdates: {e}")
        return None

def send_message(chat_id, text):
    """ارسال پیام متنی (طبق مستندات sendMessage)"""
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.post(url, json=payload, timeout=30)
    except Exception as e:
        print(f"خطا در sendMessage: {e}")

def download_file(url):
    """دانلود فایل از لینک مستقیم و ذخیره موقت"""
    resp = requests.get(url, stream=True, timeout=60)
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

def upload_file_to_rubika(file_path, file_type="File"):
    """
    مرحله 1: آپلود فایل در سرور روبیکا با requestSendFile + POST فایل
    بازگرداندن file_id در صورت موفقیت
    """
    # 1-1. درخواست آدرس آپلود
    url_req = f"{BASE_URL}/requestSendFile"
    resp = requests.post(url_req, json={"type": file_type}, timeout=30)
    if resp.status_code != 200:
        print(f"خطا در requestSendFile: {resp.text}")
        return None

    data = resp.json()
    upload_url = data.get("upload_url")
    if not upload_url:
        print(f"upload_url در پاسخ یافت نشد: {data}")
        return None

    # 1-2. آپلود فایل روی آدرس دریافتی
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        upload_resp = requests.post(upload_url, files=files, timeout=60)

    if upload_resp.status_code != 200:
        print(f"خطا در آپلود فایل: {upload_resp.text}")
        return None

    upload_data = upload_resp.json()
    file_id = upload_data.get("file_id")
    if not file_id:
        print(f"file_id در پاسخ آپلود یافت نشد: {upload_data}")
        return None

    return file_id

def send_file_to_chat(chat_id, file_id, caption=""):
    """
    مرحله 2: ارسال فایل (با file_id) به چت با sendFile
    """
    url = f"{BASE_URL}/sendFile"
    payload = {
        "chat_id": chat_id,
        "file_id": file_id,
        "text": caption
    }
    resp = requests.post(url, json=payload, timeout=30)
    return resp.json()

def process_message(chat_id, text):
    """پردازش یک پیام: اگر لینک داشت، دانلود و ارسال کن"""
    urls = URL_PATTERN.findall(text)
    if not urls:
        return

    url = urls[0]
    send_message(chat_id, "🔽 در حال دانلود فایل...")

    try:
        # دانلود از اینترنت
        file_path = download_file(url)

        # آپلود در روبیکا
        send_message(chat_id, "📤 در حال آپلود فایل در روبیکا...")
        file_id = upload_file_to_rubika(file_path)

        if file_id:
            # ارسال به کاربر
            send_file_to_chat(chat_id, file_id, "✅ فایل شما آماده است.")
        else:
            send_message(chat_id, "❌ خطا در آپلود فایل. لطفاً دوباره تلاش کنید.")

        # پاکسازی فایل موقت
        os.remove(file_path)

    except Exception as e:
        send_message(chat_id, f"❌ خطا در پردازش:\n{e}")

def main():
    print("🤖 ربات دانلودر روبیکا (نسخه رسمی API) شروع به کار کرد.")
    offset_id = None
    processed_count = 0

    while processed_count < MAX_MESSAGES_PER_RUN:
        updates = get_updates(offset_id=offset_id, limit=5)
        if not updates or "updates" not in updates:
            time.sleep(3)
            continue

        for upd in updates["updates"]:
            processed_count += 1
            if processed_count > MAX_MESSAGES_PER_RUN:
                break

            # بر اساس مستندات، ساختار Update شامل type و new_message است
            if upd.get("type") == "NewMessage":
                new_msg = upd.get("new_message", {})
                chat_id = new_msg.get("chat_id")
                text = new_msg.get("text", "")
                message_id = new_msg.get("message_id")

                if chat_id and text:
                    process_message(chat_id, text)

                # به‌روزرسانی offset_id برای دریافت پیام‌های بعدی
                if message_id:
                    offset_id = message_id

            # اگر آپدیت ساختار دیگری داشت (مثلاً InlineMessage)، از آن صرف نظر می‌کنیم

        # آفست نهایی برای درخواست بعدی (طبق مستندات: next_offset_id)
        if "next_offset_id" in updates:
            offset_id = updates["next_offset_id"]

        time.sleep(3)

    print(f"✅ پردازش {processed_count} پیام به پایان رسید. خروج...")

# ==================== تایمر خروج (مخصوص GitHub Actions) ====================
def timeout_handler(signum, frame):
    print(f"\n⏰ زمان {TIMEOUT} ثانیه تمام شد. خروج امن...")
    sys.exit(0)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(TIMEOUT)

if __name__ == "__main__":
    main()
