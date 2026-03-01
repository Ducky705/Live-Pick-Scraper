FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY live_runner.py .

# Create required directories
RUN mkdir -p data/logs data/sessions data/temp_images

# Run the listener
CMD ["python", "-u", "live_runner.py"]
