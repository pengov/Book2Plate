.PHONY: help install up down test lint format

help:
	@echo "Commandes disponibles :"
	@echo "  make install    - Installe le package en mode éditable avec dépendances dev"
	@echo "  make up         - Lance PostgreSQL (pgvector) en arrière-plan"
	@echo "  make down       - Arrête les conteneurs Docker"
	@echo "  make test       - Lance les tests unitaires pytest"
	@echo "  make lint       - Vérifie la conformité du code avec ruff"
	@echo "  make format     - Formate automatiquement le code avec ruff"

install:
	pip install -e ".[dev]"

up:
	docker compose up -d

down:
	docker compose down

test:
	pytest -v

lint:
	ruff check src tests

format:
	ruff format src tests