FROM python:3.11-slim

WORKDIR /opt/cowrie

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    python3-venv \
    libssl-dev \
    libffi-dev \
    build-essential \
    libpython3-dev \
    python3-minimal \
    libmysqlclient-dev \
    default-libmysqlclient-dev \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create cowrie user
RUN useradd -m -s /bin/bash cowrie && \
    chown -R cowrie:cowrie /opt/cowrie

USER cowrie

# Clone Cowrie
RUN git clone https://github.com/cowrie/cowrie.git /opt/cowrie

# Create virtual environment
RUN python3 -m venv cowrie-env

# Upgrade pip and install wheel first
RUN /opt/cowrie/cowrie-env/bin/pip install --upgrade pip setuptools wheel

# Install Twisted EXPLICITLY first (this is the key fix!)
RUN /opt/cowrie/cowrie-env/bin/pip install twisted

# Now install Cowrie requirements
RUN /opt/cowrie/cowrie-env/bin/pip install -r requirements.txt

# Install MySQL support
RUN /opt/cowrie/cowrie-env/bin/pip install mysqlclient

# Install Cowrie itself
RUN /opt/cowrie/cowrie-env/bin/pip install -e .

# Verify twistd is installed
RUN /opt/cowrie/cowrie-env/bin/twistd --version

# Copy default config
RUN cp etc/cowrie.cfg.dist etc/cowrie.cfg

# Create necessary directories
RUN mkdir -p var/log/cowrie var/run var/lib/cowrie/downloads var/lib/cowrie/tty

# Expose ports
EXPOSE 2222 2223

# Start Cowrie in foreground
CMD ["/opt/cowrie/cowrie-env/bin/cowrie", "start", "-n"]
