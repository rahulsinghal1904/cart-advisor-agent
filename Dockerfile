FROM --platform=linux/amd64 python:3.11-slim

# Print Python version during build
RUN python --version

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
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

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install && \
    playwright install-deps && \
    playwright install chromium

# Copy the rest of the application
COPY . .

# Set environment variables if needed
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose the port the app runs on
EXPOSE 8080

# Command to run your application
CMD ["python", "e_commerce_agent/src/e_commerce_agent/e_commerce_agent.py"]