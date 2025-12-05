from passlib.context import CryptContext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from models import User, AuditLog
from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from decimal import Decimal
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import openai


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

def money(val):
    return f"₹{val:,.2f}"

# ---------- Salary Breakup Function ----------
def breakup_salary(gross_salary: Decimal):
    basic = gross_salary * Decimal("0.50")
    hra = gross_salary * Decimal("0.20")
    special = gross_salary * Decimal("0.20")

    pf = basic * Decimal("0.12")
    professional_tax = Decimal("200.00")

    total_earnings = basic + hra + special
    total_deductions = pf + professional_tax
    net_salary = total_earnings - total_deductions

    return {
        "basic": basic,
        "hra": hra,
        "special": special,
        "pf": pf,
        "pt": professional_tax,
        "total_earnings": total_earnings,
        "total_deductions": total_deductions,
        "net_salary": net_salary
    }


def generate_pdf(employee,user, breakup):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Salary Slip</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    # Employee Info
    emp_table = [
        ["Employee Name:", user.full_name],
        ["Employee ID:", employee.id],
        ["Department:", employee.department or ""],
        ["Designation:", employee.designation or ""],
        ["Gross Salary:", money(employee.salary)]
    ]

    t1 = Table(emp_table, colWidths=[120, 300])
    t1.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 10)]))
    story.append(t1)
    story.append(Spacer(1, 20))

    # Earnings & Deductions
    earnings = [
        ["Basic", money(breakup["basic"])],
        ["HRA", money(breakup["hra"])],
        ["Special Allowance", money(breakup["special"])],
        ["Total Earnings", money(breakup["total_earnings"])]
    ]

    deductions = [
        ["PF (12% Basic)", money(breakup["pf"])],
        ["Professional Tax", money(breakup["pt"])],
        ["Total Deductions", money(breakup["total_deductions"])],
        ["Net Salary", money(breakup["net_salary"])]
    ]

    t2 = Table([
        ["Earnings", "Amount", "Deductions", "Amount"],
        ["Basic", money(breakup["basic"]), "PF", money(breakup["pf"])],
        ["HRA", money(breakup["hra"]), "Professional Tax", money(breakup["pt"])],
        ["Special Allowance", money(breakup["special"]), "", ""],
        ["Total Earnings", money(breakup["total_earnings"]), "Total Deductions", money(breakup["total_deductions"])],
        ["Net Salary", money(breakup["net_salary"]), "", ""]
    ], colWidths=[120, 120, 120, 120])

    t2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTSIZE', (0,0), (-1,-1), 10)
    ]))

    story.append(t2)

    doc.build(story)
    buffer.seek(0)
    return buffer

def create_audit_log(db, user_id, action, module, record_id,old_data=None, new_data=None, request=None):

    log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=module,
        record_id=record_id,
        old_data=old_data,
        new_data=new_data,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        created_at=datetime.now(timezone.utc)
    )

    db.add(log)
    db.commit()

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_chatgpt(prompt: str, model="gpt-3.5-turbo"):
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content