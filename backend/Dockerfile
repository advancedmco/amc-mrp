# QuickBooks Integration Backend for AMC MRP
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose backend API port
EXPOSE 5002

# Run the backend service
CMD ["python", "app.py"]
