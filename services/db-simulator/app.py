import asyncio
import random
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db-simulator")

app = FastAPI()

PRODUCTS = [
    {"id": 1, "name": "Widget A", "price": 9.99},
    {"id": 2, "name": "Widget B", "price": 19.99},
    {"id": 3, "name": "Widget C", "price": 4.99},
]


@app.get("/")
async def query():
    # Simulate realistic DB latency (10ms - 200ms)
    latency = random.uniform(0.01, 0.2)
    await asyncio.sleep(latency)

    # 10% failure rate to simulate DB errors
    if random.random() < 0.5:
        logger.error("Simulated DB connection failure!")
        return JSONResponse(
            status_code=500,
            content={"service": "db-simulator",
                     "error": "DB connection failed"}
        )

    logger.info(f"DB query completed in {latency:.3f}s")
    return {
        "service": "db-simulator",
        "latency_ms": round(latency * 1000, 2),
        "data": random.choice(PRODUCTS)
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
