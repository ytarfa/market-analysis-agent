FROM python:3.13-slim

WORKDIR /app

# Install pip dependencies without cache
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]