import os
import re
import requests
from pyrubi import Client
from pyrubi.types import Message

# ==================== تنظیمات (توکن ربات) ====================
AUTH_KEY = "vtqlafllpivpmwrootflihxtwknnfoeu"
PRIVATE_KEY = "nMIICXAIBAAKBgQC7yVXtsw+jM6w7XW+hLn3HqvCTU7pMLhsVer6GQrUn6c0bXNcP\n37OGDJzwaF2CwsrETIUEj7HcBde3k8zrZMh4e5x/8mCKGV48XLfDmXbX5EPWjCmE\nnom6xSYlJ+9oSTrfGeiZ/6aV53XjC6ZscHBCJgyMtKwG+AGIMPrpD3/VpQIDAQAB\nAoGAQk2CqPQto8Z1W9qQNP1IzMxmt+X6o7YtuuZFSftYohiTYkNj7cdiyARBD0MS\nLT6gwDFyT9t6hYCMm1U0p7JEc2b2A402wityfLNpsnSERqm1KpCnGHgiPiscDZte\ngl9qlF+Z51sXosLzjv+TmHo6L9f+eALtKeVPXnLjFt+JAOsCQQDWIoVi5bBvMOe3\ngO7j7luYeHx+EZ+fhp9vBUIYbO8CnPu5Jpl1ZPbma63bMThUoWSoRbOFGjuaqRHs\nD94xCKZPAkEA4IATEwT9AoQcG3il639eCyc2kN2d942YIH8a/fvrNmBVidrjucSV\nvjr7JN4xqPlxEChky5DsH5qLwy78K4R7ywJAOlHSlDnMUKw4H7E83tUXGzKNbWRt\nXewzVfBPrQlWGxcYM7gAiYmC+QSQqCcCmYIPQQkiuHiJjTjIycsUj7Q0XwJAJXVZ\nOWgwqxXN9st3q8aRs3y0fxFrRR3sDygGIfDBu03xl9HdA2cIsTf4JZupX49XTSHg\nR5MDwvYvcb7KNpyhZwJBAKHk2tMOT0PcSRL1ZVZas9y4kn2TaBa7ypcyA4Jw+VsC\nnNXINc3eE+naQ6ikqWUd1e/N9pauYSYB164+GW5CSE8="
# ============================================================

# تنظیمات دانلود
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

client = Client(auth=AUTH_KEY, private=PRIVATE_KEY, platform="android")

# الگوی شناسایی لینک مستقیم (شامل http/https و پسوند فایل‌های رایج)
URL_PATTERN = re.compile(r'https?://[^\s]+')

@client.on_message()
def handle_message(msg: Message):
    text = msg.text
    if not text:
        return

    # استخراج اولین لینک از متن
    urls = URL_PATTERN.findall(text)
    if not urls:
        return

    url = urls[0]
    chat_id = msg.object_guid

    # پیام "در حال دانلود..."
    client.send_text(chat_id, "🔽 در حال دانلود فایل... لطفاً صبور باشید.")

    try:
        file_path = download_file(url)
        # ارسال فایل به همان چت
        client.send_file(chat_id, file_path, caption="✅ فایل شما دانلود شد.")
        # حذف فایل موقتی (اختیاری)
        os.remove(file_path)
    except Exception as e:
        client.send_text(chat_id, f"❌ خطا در دانلود فایل:\n{e}")

def download_file(url):
    """دانلود فایل از لینک مستقیم و ذخیره در DOWNLOAD_DIR"""
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    # سعی می‌کنیم نام فایل را از Content-Disposition یا URL استخراج کنیم
    filename = None
    cd = response.headers.get('Content-Disposition')
    if cd:
        # pattern: attachment; filename="name.ext"
        fname_match = re.findall('filename="?([^";]+)"?', cd)
        if fname_match:
            filename = fname_match[-1]

    if not filename:
        # استخراج نام فایل از انتهای URL
        filename = url.split('/')[-1].split('?')[0]
        if not filename:
            filename = "downloaded_file"

    file_path = os.path.join(DOWNLOAD_DIR, filename)

    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return file_path

# اجرای ربات
print("ربات دانلودر فعال شد...")
client.run()
