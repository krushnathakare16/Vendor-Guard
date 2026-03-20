FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=200
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]