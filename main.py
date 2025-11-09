import uvicorn
import sys
import os

if __name__ == "__main__":
    # استفاده از uvicorn.run با reload=False برای جلوگیری از مشکل multiprocessing
    # Use uvicorn.run with reload=False to avoid multiprocessing issues
    # برای development، می‌توانید reload را True کنید اما باید email-validator در anaconda هم نصب باشد
    # For development, you can set reload=True but email-validator must be installed in anaconda too
    
    # راه حل موقت: غیرفعال کردن reload
    # Temporary solution: disable reload
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
    
    # برای استفاده از reload، از دستور زیر در terminal استفاده کنید:
    # To use reload, use the following command in terminal:
    # uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload