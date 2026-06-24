from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, Base
from routers.detection import router as detection_router


# ── Lifespan: pre-load both models before the first request ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs warm_up() in a thread-pool executor so the blocking model-load
    doesn't stall the asyncio event loop during startup.

    Both Mask R-CNN and YOLO are loaded once here:
      • On GPU environments  → models go to CUDA (fast inference)
      • On CPU environments  → models go to CPU  (slower but functional)
    The first real request will therefore pay only inference cost,
    not model-loading cost.
    """
    from Utils.model_cache import warm_up
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, warm_up)
    yield
    # Shutdown: nothing explicit needed — process exit frees GPU/CPU memory


# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pipe Detection API",
    description="Mask R-CNN + YOLO hybrid pipe segmentation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow all origins (React dev + Docker)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detection_router)

@app.get("/")
def root():
    return {"status": "Pipe Detection API is running 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
