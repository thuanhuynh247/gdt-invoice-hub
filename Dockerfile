# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run_local.py
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies (e.g. for sqlite, cryptography)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy project
COPY . /app/

# Create necessary directories for runtime
RUN mkdir -p /app/data /app/instance

# Expose port
EXPOSE 5000

# Run with Gunicorn instead of Flask dev server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--threads", "2", "--timeout", "120", "app:app"]
