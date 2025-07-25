# 2id8 Backend

A FastAPI-based backend application for AI-powered idea generation and evaluation. This application provides a scalable, modular architecture that efficiently integrates LLM pipelines and delivers structured outputs for seamless frontend integration.

## Features

- **AI-Powered Idea Generation**: Generate innovative ideas using OpenAI's GPT models with structured prompts
- **Comprehensive Evaluation**: Multi-criteria evaluation system with detailed scoring and recommendations
- **Idea Iteration**: Refine and improve ideas based on feedback with version tracking
- **Team Collaboration**: Team-based idea management with role-based access control
- **Feedback System**: Collect and analyze feedback with sentiment analysis
- **LLM Orchestration**: Efficient management of AI interactions with queueing and rate limiting
- **Structured Outputs**: Pydantic-based schemas for consistent API responses
- **Database Integration**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Comprehensive Logging**: Detailed logging of all AI interactions for debugging and analytics

## Architecture

The application follows a modular, layered architecture:

```
app/
├── core/           # Core configuration and dependencies
├── database/       # Database configuration and migrations
├── models/         # SQLAlchemy database models
├── schemas/        # Pydantic models and AI integration
│   ├── prompts/    # Structured prompts for LLM operations
│   └── outputs/    # Structured output models
├── routes/         # FastAPI route handlers
├── services/       # Business logic layer
├── utils/          # Utility functions and helpers
└── main.py         # FastAPI application entry point
```

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: pydantic-ai with OpenAI GPT models
- **Validation**: Pydantic for data validation and serialization
- **Migrations**: Alembic for database schema management
- **Testing**: pytest with async support
- **Containerization**: Docker
- **Logging**: Structured logging with configurable levels

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd 2id8
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up the database:
```bash
# Create database
createdb 2id8_db

# Run migrations
alembic upgrade head
```

6. Run the application:
```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Docker Deployment

1. Build the Docker image:
```bash
docker build -t 2id8-backend .
```

2. Run with Docker Compose (recommended):
```bash
# Create docker-compose.yml with PostgreSQL and app services
docker-compose up -d
```

## API Documentation

Once the application is running, visit:
- **OpenAPI/Swagger**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### Authentication & Onboarding
- `POST /api/v1/onboarding/register` - User registration
- `POST /api/v1/onboarding/login` - User authentication
- `GET /api/v1/onboarding/verify-email/{token}` - Email verification

#### Idea Generation
- `POST /api/v1/idea-generation/generate` - Generate new ideas
- `POST /api/v1/idea-generation/iterate/{idea_id}` - Iterate on existing ideas
- `GET /api/v1/idea-generation/batch-generate` - Batch idea generation

#### Evaluation
- `POST /api/v1/evaluation/evaluate/{idea_id}` - Evaluate an idea
- `POST /api/v1/evaluation/compare` - Compare multiple ideas
- `GET /api/v1/evaluation/batch-evaluate` - Batch evaluation

#### Iteration & Refinement
- `POST /api/v1/iteration/refine/{idea_id}` - Refine an idea
- `GET /api/v1/iteration/history/{idea_id}` - Get iteration history
- `POST /api/v1/iteration/branch/{idea_id}` - Create idea branch

#### Feedback
- `POST /api/v1/feedback/create` - Create feedback
- `GET /api/v1/feedback/idea/{idea_id}` - Get idea feedback
- `GET /api/v1/feedback/summary/{idea_id}` - AI-generated feedback summary

#### LLM Logs & Analytics
- `GET /api/v1/llm-logs/` - Get LLM interaction logs
- `GET /api/v1/llm-logs/analytics/usage` - Usage analytics
- `GET /api/v1/llm-logs/analytics/costs` - Cost analytics

## Configuration

Key configuration options in `.env`:

```env
# Application
APP_NAME=2id8 Backend
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/2id8_db

# OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## Database Models

### Core Models
- **User**: User accounts and authentication
- **Team**: Team collaboration and management
- **TeamMember**: Team membership with roles
- **Idea**: Generated and user-created ideas
- **LLMLog**: AI interaction tracking and analytics

### Key Relationships
- Users can belong to multiple teams
- Ideas can be individual or team-based
- All AI interactions are logged for analysis
- Ideas support versioning and iteration history

## AI Integration

The application uses pydantic-ai for structured AI interactions:

### Idea Generation
- Structured prompts with context building
- Multiple ideas per request with confidence scores
- Customizable creativity levels and constraints

### Evaluation
- Multi-criteria evaluation framework
- Detailed scoring with justifications
- Risk assessment and recommendations

### Iteration
- Feedback-driven improvements
- Change tracking and version history
- Branching for alternative explorations

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_services/test_llm_service.py
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

### Code Quality
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/
```

## Monitoring & Logging

The application provides comprehensive monitoring:

- **Health Checks**: `/health` and `/health/detailed`
- **Request Logging**: All API requests with timing
- **LLM Analytics**: Usage, costs, and performance metrics
- **Error Tracking**: Structured error logging

## Security

- JWT-based authentication
- Input validation and sanitization
- SQL injection prevention
- Rate limiting for AI API calls
- CORS configuration
- Environment-based secrets management

## Performance

- Async request handling
- Connection pooling
- LLM request queueing and prioritization
- Efficient database queries
- Response caching (where appropriate)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Add your license information here]

## Support

For questions or issues:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the logs for debugging information