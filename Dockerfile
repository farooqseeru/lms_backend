FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Make scripts executable and fix line endings
COPY wait-for-postgres.sh /app/
RUN chmod +x /app/wait-for-postgres.sh && \
    sed -i 's/\r$//' /app/wait-for-postgres.sh

COPY init_db.sh /app/
RUN chmod +x /app/init_db.sh && \
    sed -i 's/\r$//' /app/init_db.sh

# Run wait script
CMD ["bash", "/app/wait-for-postgres.sh"]
