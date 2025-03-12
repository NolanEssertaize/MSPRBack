# Plant Care Application

## Description
This application is a comprehensive plant care management system built with FastAPI. It allows users to register their plants, request plant care services from botanists, and manage plant care instructions.

## Features
- 🌱 Plant Management
  - Register new plants
  - Upload plant photos
  - Add care instructions
  - Track plant locations

- 👤 User Management
  - User registration and authentication
  - JWT token-based security
  - Role-based access (regular users and botanists)

- 🤝 Care Request System
  - Create care requests for plants
  - Match plant owners with botanists
  - Track care request status

## Technical Stack
- **Backend Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **Migration Tool**: Alembic
- **API Documentation**: Swagger/OpenAPI

## Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- virtualenv (recommended)

## Installation

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

## Running the Application

Start the application with:
```bash
uvicorn app.main:app --reload
```

The application will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Alternative documentation: http://localhost:8000/redoc

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
└── .env                     # Environment variables
```

## API Endpoints

### Authentication
- `POST /token` - Get access token
- `POST /users/` - Create new user

### Plants
- `POST /plants/` - Create new plant
- `GET /plants/` - List user's plants
- `GET /plants/{id}` - Get plant details
- `PUT /plants/{id}` - Update plant
- `DELETE /plants/{id}` - Delete plant

### Care Requests
- `POST /care-requests/` - Create care request
- `GET /care-requests/` - List care requests
- `PUT /care-requests/{id}` - Update care request status
- `DELETE /care-requests/{id}` - Cancel care request

## Testing

Run the test suite with:
```bash
pytest
```

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

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Security Notes
- Change the default SECRET_KEY in production
- Use HTTPS in production
- Implement rate limiting for production use
- Regularly update dependencies

## License
[Your License Here]

## Contact
[Your Contact Information]