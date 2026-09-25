FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY docs/schema.sql docs/schema.sql
EXPOSE 4567
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "4567"]
