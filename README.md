# Roboflow Universe Dataset Scraper

A robust, Docker-based web scraper that searches Roboflow Universe for computer vision datasets, extracts project information, and automatically downloads datasets using the Roboflow API.

## Features

- 🔍 **Smart Search**: Search Roboflow Universe with custom keywords
- 🏗️ **Robust Architecture**: Built with Playwright for reliable web scraping
- 🐳 **Docker Ready**: Complete Docker setup with PostgreSQL database
- 📊 **Database Tracking**: Prevents duplicate downloads and tracks progress
- 🔄 **API Integration**: Automatic dataset downloads via Roboflow API
- 📦 **Multiple Formats**: Supports various dataset formats (YOLOv8, COCO, etc.)
- 🚀 **Scalable**: Handles pagination and large result sets

## Quick Start

### Windows (Recommended)
```cmd
start.bat
```

### Linux/Mac
```bash
# Create environment file
cp env.example .env
# Edit .env with your Roboflow API key

# Start the scraper
docker-compose up --build
```

### Manual Setup
1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd roboflow-data-scraper
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your Roboflow API key
   ```

3. **Run with Docker**
   ```bash
   docker-compose up --build
   ```

## Configuration

### Environment Variables

Create a `.env` file from the example:

```bash
# Required: Your Roboflow API key
ROBOFLOW_API_KEY=your_api_key_here

# Optional: Search configuration
SEARCH_TERMS=bottle,plastic bottle,object detection
MAX_PAGES=3
```

### Getting a Roboflow API Key

1. Sign up at [Roboflow](https://roboflow.com)
2. Go to your account settings
3. Generate an API key
4. Add it to your `.env` file

## Usage

### With Docker (Recommended)

```bash
# Start the scraper with default settings
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f scraper

# Stop the scraper
docker-compose down
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up PostgreSQL (or update DATABASE_URL in .env)
# Run the scraper
python main.py
```

## How It Works

1. **Search Phase**: 
   - Navigates to Roboflow Universe
   - Performs searches with specified keywords
   - Extracts project information from search results

2. **Data Extraction**:
   - Parses project cards to extract metadata
   - Extracts workspace_id and project_id from URLs
   - Collects project details (title, author, image count, etc.)

3. **Database Storage**:
   - Stores project information in PostgreSQL
   - Prevents duplicate processing
   - Tracks download status

4. **Dataset Download**:
   - Uses Roboflow API to download datasets
   - Supports multiple formats (YOLOv8, COCO, Pascal VOC)
   - Organizes downloads in the `results/` folder

## Project Structure

```
roboflow-data-scraper/
├── docker-compose.yml      # Docker orchestration
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── init.sql              # Database schema
├── main.py               # Entry point
├── scraper.py            # Web scraping logic
├── roboflow_api.py       # API integration
├── database.py           # Database models
├── env.example           # Environment template
├── results/              # Downloaded datasets
└── logs/                 # Application logs
```

## Database Schema

The scraper uses PostgreSQL with two main tables:

- **projects**: Stores project metadata and download status
- **search_history**: Tracks search queries and results

## Output Structure

Downloaded datasets are organized as:
```
results/
├── workspace1_project1/
│   ├── project1_yolov8.zip
│   └── project1_yolov8/
│       ├── train/
│       ├── valid/
│       └── data.yaml
└── workspace2_project2/
    └── ...
```

## Customization

### Search Terms
Update the `SEARCH_TERMS` environment variable:
```bash
SEARCH_TERMS="car,vehicle,traffic,road signs"
```

### Dataset Format
Modify the `download_dataset` call in `scraper.py`:
```python
download_path = self.roboflow_api.download_dataset(
    workspace_id, 
    project_id, 
    format="coco"  # Change format here
)
```

### Pagination
Control how many pages to scrape:
```bash
MAX_PAGES=5
```

## Troubleshooting

### Common Issues

1. **Docker Build Issues**
   ```bash
   # Clean build without cache
   docker-compose down -v
   docker system prune -f
   docker-compose build --no-cache --pull
   ```

2. **API Key Issues**
   - Verify your API key is correct
   - Check if you have access to the projects
   - Some projects may be private

3. **Scraping Issues**
   - Roboflow may update their UI
   - Check logs for specific errors
   - Adjust selectors if needed

4. **Database Connection**
   - Ensure PostgreSQL is running
   - Check connection string in `.env`

### Logs

Check application logs:
```bash
# Docker
docker-compose logs -f scraper

# Real-time logs
docker-compose logs --tail=100 -f
```

### Logs

Check application logs:
```bash
# Docker
docker-compose logs -f scraper

# Real-time logs
docker-compose logs --tail=100 -f

# Local development
tail -f logs/scraper.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Disclaimer

This tool is for educational and research purposes. Please respect Roboflow's terms of service and rate limits. Always ensure you have permission to download and use datasets.
