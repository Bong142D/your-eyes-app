FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

EXPOSE 5005

ENV PORT=5005
ENV BILLING_ENV=dev
ENV BILLING_DB_PATH=/app/data/billing.db
# Bắt buộc để log hiện NGAY LẬP TỨC trong `docker logs` — không có dòng này, stdout của
# Python bị block-buffer khi không phải TTY, log demo có thể trễ vài giây tới cả phút.
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:5005", "app:app"]
