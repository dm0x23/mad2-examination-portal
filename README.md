
# Examination Management Portal V2 (MAD-II)

A full-stack Examination Management Portal built with Flask, SQLAlchemy (SQLite), and Vue.js.

## Project Structure

```text
backend/
  app.py             # Flask application factory & /health endpoint
  config.py          # Application configuration (SQLite URI, secrets)
  database.py        # SQLAlchemy instance initialization
  models.py          # SQLAlchemy ORM models and relationships
  seed.py            # Programmatic DB creation and initial Admin user seeding
  requirements.txt   # Python dependencies
frontend/            # Frontend application directory
.gitignore           # Git ignore rules
README.md            # Project documentation
```

## Setup & Usage (Milestone 0 & 1)

1. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Initialize Database & Seed Admin User:**
   ```bash
   python backend/seed.py
   ```
   *Note: The database (`portal.db`) and initial Admin account (`admin@portal.com` / `Admin@123`) are also ensured on application startup.*

3. **Run Backend Server:**
   ```bash
   python backend/app.py
   ```
