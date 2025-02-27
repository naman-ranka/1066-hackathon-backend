# Bill Split Backend

A Django-based backend API for a bill splitting application that uses AI to process receipts and intelligently divide expenses among participants.

## Features

- **Bill Management**: Create, read, update, and delete bills
- **Receipt OCR**: Extract text from receipt images
- **AI Processing**: Process receipts using OpenAI and Google Gemini models
- **Split Calculations**: Calculate how expenses should be split among participants
- **REST API**: Full API for integration with frontend applications

## Tech Stack

- **Framework**: Django + Django REST Framework
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **AI Services**: OpenAI GPT-4, Google Gemini
- **Image Processing**: Tesseract OCR
- **Containerization**: Docker + Docker Compose
- **Web Server**: Nginx + Gunicorn
- **SSL**: Let's Encrypt / Certbot

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (for containerized deployment)
- API keys for OpenAI and Google Gemini

## Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd 1066-hackathon-backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

## Docker Deployment

1. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

2. **Build and start the containers**:
   ```bash
   docker-compose up -d
   ```

3. **Initialize the database** (first run only):
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

## API Endpoints

### Bills
- `GET /api/bills/` - List all bills
- `POST /api/bills/` - Create a new bill
- `GET /api/bills/{id}/` - Get a specific bill
- `PUT /api/bills/{id}/` - Update a bill
- `DELETE /api/bills/{id}/` - Delete a bill

### LLM Receipt Processing
- `POST /api/llm/process-receipt/` - Process a receipt image with AI

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | Django secret key | None (required) |
| DJANGO_DEBUG | Debug mode flag | "True" |
| OPENAI_API_KEY | OpenAI API key | None |
| GEMINI_API_KEY | Google Gemini API key | None |
| DB_ENGINE | Database engine | django.db.backends.sqlite3 |

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.