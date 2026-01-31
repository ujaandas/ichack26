COMPOSE = docker compose -f infra/docker-compose.yml

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) down
	$(COMPOSE) up -d

logs:
	$(COMPOSE) logs -f

backend:
	docker exec -it hackathon_backend sh

db:
	docker exec -it hackathon_db psql -U app -d app

reset-db:
	$(COMPOSE) down -v
	rm -rf infra/db_data

prune:
	docker system prune -f