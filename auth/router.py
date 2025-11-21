from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole, Employee, StatusEnum
from utils import hash_password, verify_password, STATIC_PATHS, get_daily_quote
from datetime import date

router = APIRouter()
templates = Jinja2Templates(directory="templates")
static_paths = STATIC_PATHS
quote, author = get_daily_quote()
today = date.today()

@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, **static_paths})

@router.get("/")
async def login_page(request: Request):
    if request.session.get("user_id"):
        return templates.TemplateResponse("dashboard.html", {"request": request,**static_paths,"quote": quote,"author": author,"todays_date":today})
    return templates.TemplateResponse("login.html", {"request": request,**static_paths, "message": "","status":400})

@router.post("/")
def login_user(request: Request, email_id: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email_id, User.status == "Y").first()
    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {"request": request, **static_paths,"message": "Invalid email or password","status":400})

    # Set session
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    return templates.TemplateResponse("dashboard.html", {"request": request, **static_paths,"user": user,"quote": quote,"author": author,"todays_date":today})

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return templates.TemplateResponse("login.html", {"request": request, **static_paths,"message": "Logged Out Successfully","status":200})


@router.post("/register")
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        role_enum = UserRole(role.strip())
    except ValueError:
        return {"error": "Invalid role selected."}

    hashed_pw = hash_password(password)
    new_user = User(full_name=full_name, email=email, password=hashed_pw, role=role_enum)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return templates.TemplateResponse("register.html", {"request": request, **static_paths,"message": "Registration successful! Please login."})

@router.get("/dashboard")
async def dashboard_page(request: Request):
    if request.session.get("user_id"):
        return templates.TemplateResponse("dashboard.html", {"request": request,**static_paths,"quote": quote,"author": author,"todays_date":today})
    return templates.TemplateResponse("login.html", {"request": request,**static_paths,"status":400})

@router.get("/employee")
async def employee_page(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return templates.TemplateResponse("login.html", {"request": request,**static_paths,"status":400})
    
    return templates.TemplateResponse( "employee.html", { "request": request, **static_paths} )

@router.get("/users")
async def users_page(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return templates.TemplateResponse("login.html", {"request": request,**static_paths,"status":400})
    
    return templates.TemplateResponse( "users.html", { "request": request, **static_paths} )

@router.get("/users/data")
def users_data(db: Session = Depends(get_db)):
    data = (
        db.query(User).all()
    )

    rows = []
    for usr in data:
        icon_color = "red" if usr.status == "Y" else "green"
        rows.append({
            "full_name": usr.full_name,
            "email": usr.email,
            "role": usr.role,
            "created_on": usr.created_on.strftime("%Y-%m-%d"),
            "action": f"""
            <a class='btn btn-sm btn-primary' href='/user/edit/{usr.id}'>
                <i class='fa fa-edit' ></i>
            </a>
            &nbsp;
            <button class='btn btn-sm btn-warning updateStatus' data-id='{usr.id}'>
                <i class='fa fa-refresh' style='color:{icon_color};'></i>
            </button>
        """
        })

    return {"data": rows}
    
@router.get("/employee/data")
def employee_data(db: Session = Depends(get_db)):
    data = (
        db.query(Employee, User)
        .join(User, Employee.user_id == User.id)
        .all()
    )

    rows = []
    for emp, usr in data:
        icon_color = "red" if emp.status == "Y" else "green"
        rows.append({
            "id": emp.id,
            "full_name": usr.full_name,
            "email": usr.email,
            "phone": emp.phone,
            "department": emp.department,
            "designation": emp.designation,
            "salary": str(emp.salary),
            "hire_date": emp.hire_date.strftime("%Y-%m-%d"),
            "action": f"""
            <a class='btn btn-sm btn-primary' href='/employee/edit/{emp.id}'>
                <i class='fa fa-edit' ></i>
            </a>
            &nbsp;
            <button class='btn btn-sm btn-warning updateStatus' data-id='{emp.id}'>
                <i class='fa fa-refresh' style='color:{icon_color};'></i>
            </button>
        """
        })

    return {"data": rows}

@router.get("/employee/edit/{emp_id}")
async def edit_employee_page(emp_id: int, request: Request, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    user = db.query(User).filter(User.id == emp.user_id).first()

    if not emp:
        return templates.TemplateResponse("404.html", {"request": request})

    return templates.TemplateResponse("edit_employee.html", { "request": request, **static_paths, "emp": emp, "user": user })

@router.post("/employee/update")
async def employee_update(
    id: int = Form(...),
    full_name: str = Form(...),
    mobile: str = Form(...),
    dept: str = Form(...),
    designation: str = Form(...),
    salary: float = Form(...),
    joining_date: date = Form(...),
    db: Session = Depends(get_db)
):

    emp = db.query(Employee).filter(Employee.id == id).first()
    user = db.query(User).filter(User.id == emp.user_id).first()

    if not emp:
        return {"success": False, "message": "Employee not found"}

    # Update employee
    emp.phone = mobile
    emp.department = dept
    emp.designation = designation
    emp.salary = salary
    emp.hire_date = joining_date
    #emp.dob = dob

    # Update user table fields also
    user.full_name = full_name
    #user.email = email

    db.commit()

    return RedirectResponse("/employee", status_code=302)


@router.post("/employee/update-status")
async def update_employee_status(id: int = Form(...), db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == id).first()
    
    if not emp:
        return {"status": 404, "message": "Employee not found"}

    emp.status = "N" if emp.status == "Y" else "Y"   # Toggle
    user = db.query(User).filter(User.id == emp.user_id).first()
    if user:
        # If employee disabled, disable user
        if emp.status == "N":
            user.status = "N"
        else:
            user.status = "Y"

    db.commit()

    return { "status": 200, "new_status": emp.status, "message": "Status updated successfully" }

@router.post("/user/update-status")
async def update_user_status(id: int = Form(...), db: Session = Depends(get_db)):
    #emp = db.query(Employee).filter(Employee.id == id).first()
    usr = db.query(User).filter(User.id == id).first()
    
    if not usr:
        return {"status": 404, "message": "User not found"}

    usr.status = "N" if usr.status == "Y" else "Y"   # Toggle
    emp = None
    if usr.role == 'Employee':
        emp = db.query(Employee).filter(Employee.user_id == usr.id).first()
        if emp:
            # If employee disabled, disable user
            emp.status = usr.status
            emp_status = emp.status

    db.commit()

    return { "status": 200, "new_status": usr.status, "message": "Status updated successfully" }

@router.get("/add_employee")
async def add_employee(request: Request, message: str = None):
    if request.session.get("user_id"):
        return templates.TemplateResponse("add_employee.html", {"request": request,**static_paths,"quote": quote,"author": author,"message": message,})
    return templates.TemplateResponse("login.html", {"request": request,**static_paths,"status":400})

@router.post("/save_employee")
def save_employee(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    dob: str = Form(...),
    dept: str = Form(...),
    designation: str = Form(...),
    mobile: str = Form(...),
    salary: str = Form(...),
    joining_date: str = Form(...),
    db: Session = Depends(get_db)
):
    
    hashed_pw = hash_password(dob)
    new_user = User(full_name=full_name, email=email, password=hashed_pw, role='Employee')
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    user_id = new_user.id

    new_employee = Employee(phone=mobile, department=dept, designation=designation, salary=salary, hire_date=joining_date,dob=dob, user_id=user_id)
    db.add(new_employee)     
    db.commit()              
    db.refresh(new_employee) 

    url = "/add_employee?message=Employee%20added%20successfully!"
    return RedirectResponse(url=url, status_code=303)
    #return templates.TemplateResponse("add_employee.html", {"request": request, **static_paths,"message": "Employeem added successful!"})