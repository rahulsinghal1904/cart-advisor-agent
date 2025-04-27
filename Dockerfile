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

# Copy the application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
# PORT will be provided by Cloud Run/GCP at runtime
# Default to 8080 if not provided (GCP standard port)

# The EXPOSE directive is for documentation
# Cloud Run will automatically route traffic to $PORT
EXPOSE 8080

# Direct command to run the application - more reliable than a script
CMD ["python", "/app/e_commerce_agent/src/e_commerce_agent/app.py"]
