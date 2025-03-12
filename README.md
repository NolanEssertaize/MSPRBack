# Plant Care Application

## Description
This application is a comprehensive plant care management system built with FastAPI. It allows users to register their plants, request plant care services from botanists, and manage plant care instructions.

## Features
- 🌱 **Plant Management**
  - Register new plants
  - Upload plant photos
  - Add care instructions
  - Track plant locations

- 👤 **User Management**
  - User registration and authentication
  - JWT token-based security
  - Role-based access (regular users and botanists)

- 🤝 **Care Request System**
  - Create care requests for plants
  - Match plant owners with botanists
  - Track care request status

## Technical Stack
- **Backend Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **Migration Tool**: Alembic
- **API Documentation**: Swagger/OpenAPI
- **Containerization**: Docker and Docker Compose

## Prerequisites
- Docker and Docker Compose (for containerized deployment)
- Python 3.10 or higher (for local development)
- pip (Python package manager)
- virtualenv (recommended for local development)

## Installation and Deployment

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone [repository-url]
cd plant-care-app
```

2. Configure environment variables:
   The default configuration is in `docker-compose.yml`. For production, you should change the `SECRET_KEY`.

3. Build and start the Docker containers:
```bash
docker-compose up -d
```

4. Initialize the database (first time only):
```bash
docker-compose exec api alembic upgrade head
```

5. Access the application:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

6. Additional Docker commands:

   - View logs:
   ```bash
   docker-compose logs -f
   ```

   - Stop the application:
   ```bash
   docker-compose down
   ```

   - Rebuild after changes:
   ```bash
   docker-compose up --build -d
   ```

### Local Development Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd plant-care-app
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment file:
Create a `.env` file in the root directory with:
```env
DATABASE_URL=sqlite:///plant_care.db
SECRET_KEY=your-very-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. Initialize the database:
```bash
alembic upgrade head
```

6. Start the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Authentication
- `POST /token` - Get access token
- `POST /users/` - Create new user

### Plants
- `POST /plants/` - Create new plant
- `GET /my_plants/` - List user's plants
- `GET /all_plants/` - List all plants except user's
- `PUT /plants/{id}` - Update plant
- `DELETE /plants/` - Delete plant

### Care Requests
- `PUT /plants/{plant_id}/start-care` - Start plant care
- `PUT /plants/{plant_id}/end-care` - End plant care
- `GET /care-requests/` - List care requests

## Project Structure
```
plant_care_app/
├── alembic/                  # Database migrations
│   ├── versions/
│   └── env.py
├── app/                      # Application source code
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic models
│   └── auth.py              # Authentication logic
├── photos/                   # Uploaded plant photos
├── requirements.txt          # Project dependencies
├── alembic.ini              # Alembic configuration
├── Dockerfile               # Docker image configuration
├── docker-compose.yml       # Docker Compose configuration
├── .dockerignore            # Docker build exclusions
└── .env                     # Environment variables (local dev only)
```

## Docker Configuration Files

### Dockerfile
The Dockerfile defines how to build the application container:
- Uses Python 3.10 slim image
- Installs dependencies
- Sets up the application files
- Configures the container to run the FastAPI server

### docker-compose.yml
The docker-compose.yml file defines the services and their configuration:
- API service running the FastAPI application
- Volume mounts for persistent data (database and photos)
- Port forwarding (8000:8000)
- Environment variables configuration

### .dockerignore
Specifies which files should be excluded when building the Docker image to keep it clean and efficient.

## Development

### Adding New Features
1. Create new models in `app/models.py`
2. Create corresponding schemas in `app/schemas.py`
3. Add new endpoints in `app/main.py`
4. Create database migrations:
```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document functions and classes
- Keep functions focused and small

## Testing

Run the test suite with:
```bash
pytest
```

With Docker:
```bash
docker-compose exec api pytest
```

## Security Notes
- Change the default SECRET_KEY in production
- Use HTTPS in production
- Implement rate limiting for production use
- Regularly update dependencies

## Backup and Maintenance

### Data Backup
The application uses volumes to persist data outside the container:
- Database file (`a_rosa_je.db`)
- Plant photos directory (`photos/`)

To backup your data, simply copy these files from the host machine.

### Database Migrations
After making model changes, create and apply migrations:

With Docker:
```bash
docker-compose exec api alembic revision --autogenerate -m "Description of changes"
docker-compose exec api alembic upgrade head
```

## Troubleshooting

### Common Issues
- **Database Connection Issues**: Verify the database file exists and has proper permissions
- **Photo Upload Failures**: Check the photos directory exists and has write permissions
- **Authentication Errors**: Verify your token hasn't expired (default is 30 minutes)

### Docker Specific
- **Container Won't Start**: Check logs with `docker-compose logs -f api`
- **Volume Mount Issues**: Verify path in docker-compose.yml and directory permissions

## License
[Your License Here]

## Contact
[Your Contact Information]