from passlib.context import CryptContext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

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