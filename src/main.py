from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.formats import router as formats_router
from src.api.downloads import router as downloads_router
from src.api.tasks import router as tasks_router
from src.core.config import settings
from src.core.lifespan import lifespan

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(tasks_router)
app.include_router(formats_router)
app.include_router(downloads_router)

# StaticFiles must be mounted LAST — after all routers
app.mount("/", StaticFiles(directory="static", html=True), name="static")
