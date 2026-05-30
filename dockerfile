FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (needed for certain python packages & health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .
RUN python manage.py collectstatic --noinput
 

# Expose port
EXPOSE 8000


# Run migrations then start gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn farmflow.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
