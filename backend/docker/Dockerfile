FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 fluxauser && \
    chown -R fluxauser:fluxauser /app

USER fluxauser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
