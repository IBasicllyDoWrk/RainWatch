# RainWatch
A weather monitoring system that collects and displays real-time weather data from IoT sensors.

## Features
- Real-time weather data collection from IoT devices
- Interactive map showing weather station locations
- Live weather data display with rain chance predictions
- User authentication and device management
- Historical weather data storage and visualization

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed on your system

### Deployment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd RainWatch
   ```

2. **Deploy using Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - Open your browser and navigate to `http://localhost:8000`
   - The application will be running with persistent database storage

### Manual Docker Build

If you prefer to build and run manually:

```bash
# Build the Docker image
docker build -t rainwatch .

# Run with persistent storage
docker run -d \
  --name rainwatch \
  -p 8000:8000 \
  -v rainwatch_data:/app/data \
  -e DB_PATH=/app/data/weather.db \
  rainwatch
```

## Database Persistence

The application uses SQLite for data storage with the following persistence features:

- **Docker Volume**: Database is stored in a named Docker volume `rainwatch_data`
- **Persistent Location**: `/app/data/weather.db` inside the container
- **Environment Variable**: `DB_PATH` can be configured to change database location

### Backup Database

To backup your database:

```bash
# Copy database from Docker volume to host
docker run --rm -v rainwatch_data:/data -v $(pwd):/backup alpine cp /data/weather.db /backup/
```

### Restore Database

To restore a database backup:

```bash
# Copy database from host to Docker volume
docker run --rm -v rainwatch_data:/data -v $(pwd):/backup alpine cp /backup/weather.db /data/
```

## Development Setup

For local development without Docker:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   uvicorn main:app --reload
   ```

3. **Access at:** `http://localhost:8000`

## API Endpoints

- `POST /api/sensor-data` - Submit sensor data (requires deviceCode header)
- `GET /api/devices` - Get all registered devices
- `GET /api/devices/{device_id}/latest` - Get latest reading for a device

## Environment Variables

- `DB_PATH` - Database file path (default: `./weather.db`)
- `SECRET_KEY` - JWT secret key (auto-generated if not set)

## Health Check

The Docker container includes a health check endpoint that verifies the application is running correctly.

## Troubleshooting

### Container won't start
- Check Docker logs: `docker-compose logs rainwatch`
- Ensure port 8000 is not already in use

### Database issues
- Verify volume permissions
- Check database path configuration
- Review application logs for SQLite errors

### Performance issues
- Monitor container resources: `docker stats`
- Consider scaling with multiple replicas if needed
