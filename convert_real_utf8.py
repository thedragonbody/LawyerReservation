import chardet  # اگر نصب نکردی: pip install chardet

input_file = r"E:\2VAKIL\AloVakil\data.json"
output_file = r"E:\2VAKIL\AloVakil\data_utf8.json"

# مرحله 1: تشخیص encoding اصلی
with open(input_file, "rb") as f:
    raw_data = f.read()
    result = chardet.detect(raw_data)
    original_encoding = result['encoding']
    print("Encoding اصلی فایل:", original_encoding)

# مرحله 2: تبدیل به UTF-8
with open(output_file, "w", encoding="utf-8") as f:
    f.write(raw_data.decode(original_encoding))

print("فایل UTF-8 ساخته شد:", output_file)