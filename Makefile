.PHONY: run test docker-up docker-test

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

docker-up:
	docker compose up --build

docker-test:
	docker compose run --rm app pytest tests/ -v
