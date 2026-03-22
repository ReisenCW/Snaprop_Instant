# 阿里云OCR配置
import os
ocr_api_id = os.getenv("ALI_OCR_API_ID")
ocr_api_secret = os.getenv("ALI_OCR_API_SECRET")

if __name__ == "__main__":
    print(ocr_api_id)
    print(ocr_api_secret)