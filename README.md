# Loan Management System (LMS)

A comprehensive loan management system with features for user management, loan accounts, card management, transactions, and rewards.

## Prerequisites

Before you begin, ensure you have the following installed:
- Docker and Docker Compose
- Python 3.8 or higher
- Git

## Project Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd lms_project
   ```

2. **Environment Setup**
   - Create a virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate  # On Windows, use: venv\Scripts\activate
     ```
   - Install Python dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. **Database Setup**
   - The project uses PostgreSQL with Docker Compose
   - Start the database and API services:
     ```bash
     docker-compose up -d
     ```
   - This will start:
     - PostgreSQL database
     - API service
     - Any other required services

4. **Database Migrations**
   - Apply database migrations:
     ```bash
     docker-compose exec api alembic upgrade head
     ```

## Running the Project

1. **Start the Services**
   ```bash
   docker-compose up -d
   ```

2. **Verify Services are Running**
   ```bash
   docker-compose ps
   ```
   You should see all services in "Up" state.

3. **Access the API**
   - The API will be available at: `http://localhost:8000`
   - API documentation (Swagger UI): `http://localhost:8000/docs`

## Testing the System

1. **Run the Test Script**
   ```bash
   python3 test_script.py
   ```
   This will:
   - Create sample users
   - Create loan accounts
   - Create cards
   - Simulate transactions
   - Demonstrate repayments
   - Show reward system functionality

## Project Structure

```
lms_project/
├── app/                    # Main application code
│   ├── api/               # API routes and endpoints
│   ├── core/              # Core functionality
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   └── services/          # Business logic
├── migrations/            # Database migrations
├── tests/                 # Test files
├── docker-compose.yml     # Docker configuration
├── Dockerfile            # API service Dockerfile
├── requirements.txt      # Python dependencies
└── test_script.py        # Test script
```

## Key Features

- User Management
- Loan Account Management
- Card Management (Virtual & Physical)
- Transaction Processing
- Interest Calculation
- Repayment System
- Reward System (APR Reduction)
- Statement Generation

## Troubleshooting

1. **Database Connection Issues**
   - Check if PostgreSQL container is running:
     ```bash
     docker-compose ps
     ```
   - View logs:
     ```bash
     docker-compose logs db
     ```

2. **API Issues**
   - Check API logs:
     ```bash
     docker-compose logs api
     ```
   - Restart API service:
     ```bash
     docker-compose restart api
     ```

3. **Common Errors**
   - "Connection refused": Ensure all services are running
   - "Database not found": Check if migrations were applied
   - "Port already in use": Stop other services using port 8000

## Development Guidelines

1. **Code Style**
   - Follow PEP 8 guidelines
   - Use type hints
   - Document functions and classes

2. **Database Changes**
   - Create new migrations for schema changes:
     ```bash
     docker-compose exec api alembic revision --autogenerate -m "description"
     ```
   - Apply migrations:
     ```bash
     docker-compose exec api alembic upgrade head
     ```

3. **Testing**
   - Run tests:
     ```bash
     docker-compose exec api pytest
     ```

## Support

For any issues or questions, please contact the development team.

## License

[Add your license information here] 