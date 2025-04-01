# Expense Tracker API

This is the backend API for the Expense Tracker application. It provides endpoints for user authentication, receipt upload, and expense tracking.

## Features

- User authentication (registration, login)
- Receipt image upload and processing using AWS Textract
- Receipt data management (create, read, update, delete)
- Expense categorization and tracking

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **Image Processing**: AWS Textract
- **Containerization**: Docker & Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- AWS account with Textract access
- Python 3.9+ (for local development without Docker)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/expense-tracker-api.git
   cd expense-tracker-api
   ```

2. Create a `.env` file based on the provided `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. Update the `.env` file with your AWS credentials and other settings

4. Start the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

5. The API should now be available at http://localhost:8000

### API Documentation

After starting the application, you can access:
- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

## Development

### Running Migrations

Migrations are handled using Alembic:

```bash
# Generate a new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec api alembic upgrade head
```

### Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run tests with coverage report
docker-compose exec api pytest --cov=app
```

## Project Structure

```
expense-tracker-api/
├── app/                  # Main application
│   ├── api/              # API endpoints
│   ├── core/             # Core functionality
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── utils/            # Utility functions
├── migrations/           # Database migrations
├── tests/                # Test suite
├── .env.example          # Environment variables template
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
└── requirements.txt      # Python dependencies
```

## Next Steps

- [ ] Implement background tasks for receipt processing
- [ ] Add reporting and analytics endpoints
- [ ] Implement budget tracking features
- [ ] Add support for receipt sharing between users
- [ ] Implement notification system