import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
from app.domains.workflow.router import router as workflow_router
from app.domains.records.router import router as records_router
from app.domains.catalogs.router import router as catalogs_router
from app.domains.users.router import router as users_router
from app.bff.router import router as bff_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Domain routers
app.include_router(
    workflow_router,
    prefix=f"{settings.API_V1_PREFIX}/workflow",
    tags=["workflow"],
)
app.include_router(
    records_router,
    prefix=f"{settings.API_V1_PREFIX}/records",
    tags=["records"],
)
app.include_router(
    catalogs_router,
    prefix=f"{settings.API_V1_PREFIX}/catalogs",
    tags=["catalogs"],
)
app.include_router(
    users_router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["users"],
)

# BFF router
app.include_router(
    bff_router,
    prefix=f"{settings.API_V1_PREFIX}/bff",
    tags=["bff"],
)
