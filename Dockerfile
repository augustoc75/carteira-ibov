# Use the official Playwright image which includes Python and browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Chromium is installed for Playwright
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Run the application
# Cloud Run usually defaults to port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]