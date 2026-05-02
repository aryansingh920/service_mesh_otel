import httpx
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("frontend")

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
    # Forward Istio trace headers to backend
    headers = {
        h: request.headers[h]
        for h in ISTIO_HEADERS
        if h in request.headers
    }

    logger.info("Frontend received request, calling backend...")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "http://backend.mesh-apps.svc.cluster.local",
                headers=headers
            )
            backend_data = response.json()
    except Exception as e:
        logger.error(f"Backend call failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"service": "frontend", "error": str(e)}
        )

    return {
        "service": "frontend",
        "message": "I am the Frontend",
        "backend": backend_data
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
