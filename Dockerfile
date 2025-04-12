FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY certs/ certs/

EXPOSE 18000

CMD ["python", "main.py"]

