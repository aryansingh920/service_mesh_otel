# Build all three images
docker build -t frontend:v1 ./services/frontend
docker build -t backend:v1 ./services/backend
docker build -t db-simulator:v1 ./services/db-simulator

# Load into Kind (no registry needed)
kind load docker-image frontend:v1 --name observability-mesh
kind load docker-image backend:v1 --name observability-mesh
kind load docker-image db-simulator:v1 --name observability-mesh
