from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import init_pool, close_pool
from app.routes import auth, notifications, projects, tasks

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()

app = FastAPI(title="TaskMaster", version="1.0.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(tasks.assigned_router)
app.include_router(notifications.router)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "TaskMaster"}
