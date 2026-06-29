FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5005

ENV PORT=5005
ENV BILLING_ENV=dev
ENV BILLING_DB_PATH=/app/data/billing.db

CMD ["python", "app.py"]