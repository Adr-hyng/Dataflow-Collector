@echo off
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              Roboflow Scraper Test Setup                     ║
echo ║                                                              ║
echo ║  This will install Playwright and test the scraper           ║
echo ║  without database - just to see how it works                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed or not in PATH
    echo    Please install Python 3.9+ and try again
    echo    Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python is installed

REM Install Playwright
echo 📦 Installing Playwright...
pip install playwright
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install Playwright
    pause
    exit /b 1
)

REM Install Playwright browsers
echo 🎭 Installing Playwright browsers...
python -m playwright install chromium
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install Playwright browsers
    pause
    exit /b 1
)

echo ✅ Setup complete!
echo.
echo 🚀 Starting test scraper...
echo 📺 A browser window will open shortly...
echo 👀 You'll be able to see exactly what the scraper is doing
echo.

REM Run the test
python test_scraper.py

echo.
echo ✅ Test completed!
echo 📁 Check the 'test_results' folder for screenshots
pause
