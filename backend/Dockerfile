FROM debian:bullseye-slim

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    fontforge \
    python3-fontforge \
    potrace \
    libcairo2-dev \
    pkg-config \
    libopencv-dev \
    libxml2-dev \
    libxslt1-dev \
    build-essential \
    python3-dev \
    libagg-dev \
    libpotrace-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a virtual environment
RUN python3 -m venv /app/venv

# Make the virtual environment use system packages
RUN echo "include-system-site-packages = true" >> /app/venv/pyvenv.cfg

# Verify fontforge installation
RUN /app/venv/bin/python -c "import fontforge; print('success this works')"

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies in the virtual environment
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Install pypotrace from source in the virtual environment
RUN git clone https://github.com/flupke/pypotrace.git && \
    cd pypotrace && \
    /app/venv/bin/pip install numpy && \
    /app/venv/bin/pip install . && \
    cd .. && \
    rm -rf pypotrace

# Copy backend code
COPY backend/ .

# Expose port
EXPOSE 8000

# Start the application using the virtual environment Python
CMD /app/venv/bin/python -m uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000} 