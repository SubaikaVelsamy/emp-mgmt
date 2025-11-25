from passlib.context import CryptContext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from models import User
from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

STATIC_PATHS = {
    "apple_icon": "/static/img/apple-icon.png",
    "favicon": "/static/img/favicon.png",
    "nucleo_icon": "/static/css/nucleo-icons.css",
    "nucleo_svg": "/static/css/nucleo-svg.css",
    "tailwind": "/static/css/soft-ui-dashboard-tailwind.css",
    "scrollbar_min": "/static/js/plugins/perfect-scrollbar.min.js",
    "tailwind_js": "/static/js/soft-ui-dashboard-tailwind.js"
}

def get_daily_quote():
    options = Options()
    options.add_argument("--headless")  # optional → run without opening a window
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://quotes.toscrape.com/")

    quote = driver.find_element(By.CLASS_NAME, "text").text
    author = driver.find_element(By.CLASS_NAME, "author").text

    driver.quit()
    return quote, author

def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()

def require_roles(*allowed_roles):
    def role_checker(request: Request, db: Session = Depends(get_db)):
        user = get_current_user(request, db)

        if not user:
            raise HTTPException(status_code=401, detail="Login required")

        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access denied")

        return user

    return role_checker

ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "application/pdf"
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
