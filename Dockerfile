FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ .

# Expose port (configurable via environment)
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
