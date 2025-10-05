import os
import sys
import subprocess

# مسیر پروژه
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AloVakil.settings")

def convert_json_to_utf8(input_file="data.json", output_file="data_utf8.json"):
    with open(input_file, "rb") as f:
        content = f.read()
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content.decode("utf-8-sig"))
    print(f"[+] فایل UTF-8 ساخته شد: {output_file}")
    return output_file

def load_fixture(fixture_file):
    print(f"[+] شروع بارگذاری fixture: {fixture_file}")
    subprocess.run([sys.executable, "manage.py", "loaddata", fixture_file])
    print("[+] بارگذاری fixture کامل شد!")

if __name__ == "__main__":
    fixture_utf8 = convert_json_to_utf8("data.json", "data_utf8.json")
    load_fixture(fixture_utf8)