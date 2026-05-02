import httpx
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

ISTIO_HEADERS = [
    "x-request-id",
    "x-b3-traceid",
    "x-b3-spanid",
    "x-b3-parentspanid",
    "x-b3-sampled",
    "x-b3-flags",
    "x-forwarded-for",
]


@app.get("/")
async def home(request: Request):
    headers = {
        h: request.headers[h]
        for h in ISTIO_HEADERS
        if h in request.headers
    }

    logger.info("Backend received request, calling db-simulator...")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "http://db-simulator.mesh-apps.svc.cluster.local",
                headers=headers
            )
            db_data = response.json()
    except Exception as e:
        logger.error(f"DB call failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"service": "backend", "error": str(e)}
        )

    return {
        "service": "backend",
        "message": "I am the Backend API",
        "db": db_data
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
