FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-jdk \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package
RUN pip install --upgrade pip && pip install -e .

# Set up the SMT-LIB grammar
RUN grammar-uncertainty setup smtlib

# Create data directory for mounted volumes
RUN mkdir -p /data

# Expose the API port
EXPOSE 8000

# Default command: start the API server
CMD ["grammar-uncertainty", "serve", "--host", "0.0.0.0", "--port", "8000"]
