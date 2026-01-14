.PHONY: install run test test-backend test-frontend test-e2e clean

install:
	pip install -r phase1/requirements.txt
	cd frontend && npm install

run:
	./run_all.sh

test-backend:
	cd phase1 && pytest

test-frontend:
	cd frontend && npm run test

test-e2e:
	cd frontend && npm run test:e2e

test: test-backend test-e2e

clean:
	rm -rf phase1/__pycache__
	rm -rf frontend/dist
	rm -rf frontend/node_modules
