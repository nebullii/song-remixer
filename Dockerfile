# Use Python 3.10 slim image
FROM python:3.10-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p output

# Expose port (Cloud Run will set PORT env var)
ENV PORT=8080

# Run the application with gunicorn
# - 1 worker (to stay in free tier)
# - 4 threads (handle concurrent requests)
# - 600s timeout (10 minutes for song generation)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 600 app:app
