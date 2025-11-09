# اسکریپت اجرای برنامه با استفاده از Python 3.13.2 در محیط مجازی
# Run script using Python 3.13.2 in virtual environment

Write-Host "فعال‌سازی محیط مجازی با Python 3.13.2..." -ForegroundColor Green
Write-Host "Activating virtual environment with Python 3.13.2..." -ForegroundColor Green

# نمایش نسخه Python
Write-Host "Python version:" -ForegroundColor Cyan
& .\env\Scripts\python.exe --version

Write-Host "`nاجرای برنامه با uvicorn..." -ForegroundColor Green
Write-Host "Running application with uvicorn...`n" -ForegroundColor Green

# اجرای برنامه با uvicorn CLI (این روش reload را به درستی مدیریت می‌کند)
# Run application with uvicorn CLI (this method properly handles reload)
& .\env\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

