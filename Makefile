.PHONY: env-backend env-frontend setup-backend setup-frontend run-backend run-frontend run-local-dev

BACKEND_DEPS = fastapi openai pydantic python-dotenv uvicorn websockets

env-backend:
	@if [ ! -f backend/.env ]; then \
		printf "OPENAI_API_KEY=your_key_here\nCORS_ORIGINS=http://localhost:3000\n" > backend/.env; \
		echo "Created backend/.env (update OPENAI_API_KEY)"; \
	else \
		echo "backend/.env already exists"; \
	fi

env-frontend:
	@if [ ! -f frontend/.env.local ]; then \
		printf "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1\nNEXT_PUBLIC_WS_URL=ws://localhost:8000\n" > frontend/.env.local; \
		echo "Created frontend/.env.local"; \
	else \
		echo "frontend/.env.local already exists"; \
	fi

setup-backend:
	@cd backend && \
	if command -v uv >/dev/null 2>&1; then \
		uv venv .venv && . .venv/bin/activate && uv pip install $(BACKEND_DEPS); \
	else \
		python3 -m venv .venv && . .venv/bin/activate && pip install $(BACKEND_DEPS); \
	fi

setup-frontend:
	@cd frontend && npm install

run-backend: env-backend
	@cd backend && \
	if command -v uv >/dev/null 2>&1; then \
		uv venv .venv >/dev/null 2>&1 || true; \
		. .venv/bin/activate && uv pip install $(BACKEND_DEPS) && uvicorn server:app --reload --port 8000; \
	else \
		python3 -m venv .venv >/dev/null 2>&1 || true; \
		. .venv/bin/activate && pip install $(BACKEND_DEPS) && uvicorn server:app --reload --port 8000; \
	fi

run-frontend: env-frontend
	@cd frontend && npm install && npm run dev

run-local-dev:
	@$(MAKE) -j2 run-backend run-frontend
