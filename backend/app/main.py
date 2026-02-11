import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.actions import action_functions
from app.api.routes import router as workspace_router
from app.engine.action_registry import ActionRegistry

logger = logging.getLogger("uvicorn.error")

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup: log built-in actions and available samples ---
    registry = ActionRegistry()
    registry.register_from_module(action_functions)
    names = registry.list_actions()
    logger.info("已加载 %d 个内置 Action 函数: %s", len(names), names)

    if SAMPLES_DIR.is_dir():
        samples = [p.stem for p in sorted(SAMPLES_DIR.glob("*.json"))]
        logger.info("可用示例数据: %s", samples)
    else:
        logger.warning("示例数据目录不存在: %s", SAMPLES_DIR)

    yield


app = FastAPI(
    title="动态图谱洞察沙盘 POC",
    description="Palantir Ontology Simulator - 动态业务推演沙盘",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspace_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
