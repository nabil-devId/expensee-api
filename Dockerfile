FROM python:3.9-slim

WORKDIR /app/

# Install system dependencies including tesseract-ocr
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TESSERACT_CMD=/usr/bin/tesseract

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Create temp directory for image processing
RUN mkdir -p /app/temp

# Copy application code
COPY . /app/

# Create non-root user for running the app
RUN groupadd -r app && useradd -r -g app app
# Give permissions to the temp directory
RUN chmod -R 755 /app/temp
RUN chown -R app:app /app
USER app

# Run the application
# Change port to 8080 for Elastic Beanstalk
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]