@echo off
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                 Roboflow Universe Scraper                    ║
echo ║                      Clean Docker Setup                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check if .env file exists
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env.example .env
    echo.
    echo ⚠️  IMPORTANT: Please edit .env file and add your ROBOFLOW_API_KEY
    echo    Example: ROBOFLOW_API_KEY=your_key_here
    echo.
    pause
)

REM Clean up any existing containers
echo 🧹 Cleaning up previous containers...
docker-compose down -v 2>nul

REM Build and start
echo 🏗️  Building and starting containers...
docker-compose up --build

echo.
echo ✅ Setup complete!
echo 📝 To view logs: docker-compose logs -f scraper
echo 🛑 To stop: docker-compose down
pause
