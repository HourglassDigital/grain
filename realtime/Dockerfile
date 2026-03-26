FROM python:3.12-slim

WORKDIR /app

# Install deps first for caching
COPY realtime/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY realtime/ ./realtime/

# Health check dependency
RUN pip install --no-cache-dir requests

CMD ["python", "-m", "realtime.app"]
