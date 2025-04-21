FROM python:3.11-slim

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only backend deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend code
COPY . .

# Default command: Run backend script
CMD ["python", "src/core/sensor_reader.py"]
