# Dockerfile

# 1) Use Ubuntu 22.04 as a base (KiCad 7 PPA only supports jammy)
FROM ubuntu:22.04

# 2) Prevent any interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# 3) Update & install prerequisites (KiCad, Python, pip, etc.)
RUN apt-get update && apt-get install -y \
    wget \
    software-properties-common \
    gnupg2 \
    python3 \
    python3-pip \
    python3-venv \
    git \
    && add-apt-repository --yes ppa:kicad/kicad-7.0-releases \
    && apt-get update && apt-get install -y \
    kicad \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4) Create app directory
WORKDIR /app

# 5) Copy only Python dependency files first (for better caching)
COPY requirements.txt /app/requirements.txt

# 6) Create a Python virtual environment and install dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 7) Copy the rest of the application code
COPY . /app

# 8) Ensure output directory exists
RUN mkdir -p /app/output

# 9) Expose port 8080
EXPOSE 8080

# 10) Run Gunicorn as the entrypoint
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
