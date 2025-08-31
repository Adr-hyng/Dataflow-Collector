# Alternative Dockerfile using Ubuntu base
FROM ubuntu:20.04

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    wget \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Create an unprivileged user
RUN useradd --create-home appuser

WORKDIR /home/appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers BEFORE switching to unprivileged user
RUN playwright install chromium
RUN playwright install-deps

# Copy application code
COPY . .

# Create directories with proper permissions
RUN mkdir -p /home/appuser/results /home/appuser/logs && \
    chmod 755 /home/appuser/results /home/appuser/logs

# Set proper permissions
RUN chown -R appuser:appuser /home/appuser

# Switch to unprivileged user
USER appuser

# Run the scraper
CMD ["python", "main.py"]
