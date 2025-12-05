from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from auth.router import router as auth_router
from utils import  STATIC_PATHS
from middleware.auth_middleware import UserRoleMiddleware
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@asynccontextmanager
async def lifespan(app: FastAPI):

    # --- Startup ---
    redis = aioredis.from_url(
        "redis://localhost:6379",
        encoding="utf-8",
        decode_responses=True
    )

    FastAPICache.init(
        RedisBackend(redis),
        prefix="emp_cache"
    )

    print("✅ Redis Cache Initialized")

    yield

    # --- Shutdown ---
    await redis.close()
    print("🛑 Redis connection closed")


app = FastAPI(lifespan=lifespan)
app.add_middleware(UserRoleMiddleware)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
# Include auth router
app.include_router(auth_router)

templates = Jinja2Templates(directory="templates")
static_paths = STATIC_PATHS

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, **static_paths})

@app.get("/")
async def login_page(request: Request):
    # Render login page
    return templates.TemplateResponse("login.html", {"request": request,**static_paths, "message": None})

@app.get("/dashboard")
async def dashboard_page(request: Request):
    # Render login page
    return templates.TemplateResponse("dashboard.html", {"request": request,**static_paths, "message": None})

@app.get("/employee")
async def employee_page(request: Request):
    # Render login page
    return templates.TemplateResponse("employee.html", {"request": request,**static_paths, "message": None})

@app.get("/add_employee")
async def add_employee_page(request: Request):
    # Render login page
    return templates.TemplateResponse("add_employee.html", {"request": request,**static_paths, "message": None})