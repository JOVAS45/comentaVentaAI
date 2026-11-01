# Atajos opcionales. En Windows (sin make) usar los comandos docker compose directos.

up:            ## construir y levantar todo (entrena la primera vez)
	docker compose up --build -d
	@echo "Frontend: http://localhost:$${FRONTEND_PORT:-8080}   API: http://localhost:$${API_PORT:-8000}/api/docs"

train:         ## reentrenar con el params.yaml actual y reiniciar la API
	docker compose run --rm trainer python -m src.pipeline
	docker compose restart api

reload-data:   ## recargar el CSV crudo en PostgreSQL y reentrenar
	docker compose run --rm trainer python -m src.pipeline --reload-data
	docker compose restart api

test:          ## pruebas automatizadas
	docker compose --profile dev run --rm --build tests

frontend:      ## reconstruir el frontend tras cambios en frontend/
	docker compose up -d --build frontend

notebook:      ## JupyterLab en http://localhost:8888
	docker compose --profile dev up --build notebook

logs:          ## seguir los logs de api y trainer
	docker compose logs -f api trainer

down:          ## detener los contenedores (conserva la base)
	docker compose down

clean:         ## detener, borrar el volumen de la base y los artefactos
	docker compose down -v
	find artifacts -type f ! -name .gitkeep -delete

.PHONY: up train reload-data test frontend notebook logs down clean
