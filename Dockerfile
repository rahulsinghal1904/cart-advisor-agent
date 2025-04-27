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
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install playwright && \
    python -m playwright install && \
    playwright install-deps

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the startup script and make it executable
COPY startup.sh .
RUN chmod +x /app/startup.sh

# Copy the rest of the application
COPY . .

# Set environment variables if needed
ENV PYTHONPATH=/app
# Don't hardcode PORT - Cloud Run will provide this

# Port 8080 is just a default for documentation
# The actual port will be read from the PORT environment variable
EXPOSE 8080

# Command to run the startup script
CMD ["/app/startup.sh"]
