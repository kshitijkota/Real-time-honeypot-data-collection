#!/bin/bash

echo "=== Cowrie Honeypot Setup ==="

# Create necessary directories
mkdir -p config sql cowrie-logs cowrie-downloads cowrie-tty

# Check if files exist
if [ ! -f "config/cowrie.cfg" ]; then
    echo "❌ Please create config/cowrie.cfg file"
    exit 1
fi

if [ ! -f "sql/init.sql" ]; then
    echo "❌ Please create sql/init.sql file"
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down -v

# Build the image
echo "🔨 Building Cowrie image..."
docker-compose build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 15

# Check status
echo "📊 Service status:"
docker-compose ps

# Show logs
echo "📋 Cowrie logs:"
docker-compose logs cowrie | tail -n 20

echo ""
echo "✅ Setup complete!"
echo "SSH Honeypot: localhost:2222"
echo "Telnet Honeypot: localhost:2223"
echo "MySQL: localhost:3306"
echo ""
echo "To view live logs: docker-compose logs -f cowrie"
echo "To test SSH: ssh -p 2222 root@localhost (password: 123456)"
