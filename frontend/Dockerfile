# Web Dashboard and Document Generator for AMC MRP
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for document generation
# pandoc: Markdown/document conversion
# texlive-xetex: PDF generation with LaTeX
# libreoffice-writer: DOCX to PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create CACHE directory for generated documents
RUN mkdir -p /app/CACHE

# Expose Flask port
EXPOSE 5000

# Run the Flask application
CMD ["python", "run.py"]
