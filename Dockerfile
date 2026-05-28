FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/fonts
COPY Lora-Bold.ttf /app/fonts/
COPY Lora-Regular.ttf /app/fonts/

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
