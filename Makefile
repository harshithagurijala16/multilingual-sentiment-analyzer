.PHONY: install run seed test docker-build docker-up docker-down clean

# Install python dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Run FastAPI development server
run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Seed SQLite database with demo user, products, and 120+ multilingual reviews
seed:
	python scripts/seed.py

# Run offline pytest test suite
test:
	pytest tests/ -v

# Build Docker image
docker-build:
	docker-compose build

# Start Docker container in background
docker-up:
	docker-compose up -d

# Stop Docker container
docker-down:
	docker-compose down

# Clean Python bytecode and pytest cache
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
