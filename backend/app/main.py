from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as workspace_router

app = FastAPI(
    title="动态图谱洞察沙盘 POC",
    description="Palantir Ontology Simulator - 动态业务推演沙盘",
    version="0.1.0",
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
