FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && \
    apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libxshmfence1 \
    wget \
    curl \
    fonts-liberation \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pip and playwright
RUN pip install --upgrade pip && \
    pip install playwright && \
    playwright install chromium

# Copy requirements.txt first and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the startup script and make it executable
COPY startup.sh .
RUN chmod +x /app/startup.sh

# Copy rest of the application
COPY . .

# Environment variables
ENV PYTHONPATH=/app

# Expose the port Cloud Run expects
EXPOSE 8080

# Start your app via the startup script
CMD ["/app/startup.sh"]
