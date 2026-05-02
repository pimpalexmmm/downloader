import requests
import os
import re
from urllib.parse import unquote, urlparse

# لینک مستقیم فایل را اینجا بگذارید
DOWNLOAD_URL = "https://github.com/Hidden-Node/GooseRelayVPN-AndroidClient/releases/download/v1.0.1/GooseRelayVPN-HN-1.0.1-universal-release.apk"

def download_file(url, save_dir="."):
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ خطا در دانلود: {e}")
        exit(1)

    # استخراج نام فایل از Content-Disposition یا URL
    filename = None
    cd = response.headers.get("Content-Disposition")
    if cd:
        # حالت filename*=UTF-8''name
        if "filename*=" in cd:
            match = re.search(r"filename\*=(?:UTF-8''|utf-8'')(.+?)(?:;|$)", cd, re.IGNORECASE)
            if match:
                filename = unquote(match.group(1))
        # حالت filename="name"
        else:
            match = re.search(r'filename="?(.+?)"?$', cd)
            if match:
                filename = match.group(1)
    if not filename:
        filename = os.path.basename(urlparse(url).path) or "downloaded_file"

    file_path = os.path.join(save_dir, filename)
    print(f"⬇️ در حال دانلود {filename} ...")
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"✅ فایل در {file_path} ذخیره شد.")
    return filename

if __name__ == "__main__":
    download_file(DOWNLOAD_URL)
