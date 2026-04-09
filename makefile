.PHONY: dev prod down clean

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build

down:
	docker compose down

clean:
	docker compose down --volumes --remove-orphans