# Gunakan image Python resmi
FROM python:3.12-slim

# Set working directory
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variable untuk Python
ENV PYTHONUNBUFFERED=1

# Jalankan bot
CMD ["python", "main.py"]
