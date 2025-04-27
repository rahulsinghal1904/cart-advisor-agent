FROM --platform=linux/amd64 python:3.11-slim
FROM mcr.microsoft.com/playwright/python:v1.51.1-jammy

# Set working directory
WORKDIR /app

# Install Playwright first (before requirements.txt)
RUN pip install playwright

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install

# Copy the rest of the application
COPY . .

# Set environment variables if needed
ENV PYTHONPATH=/app
ENV PORT=8000

# Expose the port the app runs on
EXPOSE 8080

# Command to run your application
CMD ["python", "src/e_commerce_agent/main.py"]
