FROM python:3.11-slim

WORKDIR /app

COPY requirements/requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["uvicorn", "app.api.api:app", "--host", "0.0.0.0", "--port", "8080"]