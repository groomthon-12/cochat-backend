from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import briefing, integrations, notifications, streams
from app.ingress.discord_gateway import start_gateway, stop_gateway
from app.ingress.slack_webhook import router as slack_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    discord_task = await start_gateway()
    yield
    await stop_gateway(discord_task)


app = FastAPI(
    title="CoChat API",
    description="여러 업무 채널의 알림을 통합하고 AI로 요약해 주는 CoChat 서비스의 백엔드 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(integrations.router, prefix="/api/v1")
app.include_router(slack_router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(streams.router, prefix="/api/v1")
app.include_router(briefing.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
