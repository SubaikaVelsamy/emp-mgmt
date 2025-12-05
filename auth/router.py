from fastapi import APIRouter, Request, Form, Depends, status, UploadFile, HTTPException, FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from database import get_db, get_all_employees  
from models import User, UserRole, Employee, StatusEnum
from utils import hash_password, verify_password, STATIC_PATHS, get_daily_quote, require_roles, get_current_user, ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE, money, breakup_salary, generate_pdf, create_audit_log, ask_chatgpt
from datetime import date
import os
import uuid
from decimal import Decimal
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from sqlalchemy.exc import SQLAlchemyError
import traceback
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from openai import OpenAIError, RateLimitError
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis


router = APIRouter()
templates = Jinja2Templates(directory="templates")
static_paths = STATIC_PATHS
quote, author = get_daily_quote()
today = date.today()


class ChatRequest(BaseModel):
    question: str

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
    request.session["role"] = user.role 
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
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail=f"User with email {email} already exists.")
        role_enum = UserRole(role.strip())
    except ValueError:
        return {"error": "Invalid role selected."}

    hashed_pw = hash_password(password)
    new_user = User(full_name=full_name, email=email, password=hashed_pw, role=role_enum)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse("/users", status_code=302)

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
@cache(expire=120)
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
@cache(expire=120)
def employee_data(request:Request, db: Session = Depends(get_db)):
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    if role == 'Employee':
        emp_user  = (
        db.query(Employee, User)
        .join(User, Employee.user_id == User.id)
        .filter(Employee.user_id == user_id).first()
    )
        data = [emp_user] if emp_user else []  
    else:
        data = (
            db.query(Employee, User)
            .join(User, Employee.user_id == User.id)
            .all()
        )

    rows = []
    for emp, usr in data:
        icon_color = "red" if emp.status == "Y" else "green"
        if emp.id_proof:
            preview_icon = f"""
                <button class='btn btn-sm btn-info'
                    data-bs-toggle="modal"
        data-bs-target="#idProofModal"
        onclick="loadIDProof('{emp.id_proof}')">
                    <i class='fa fa-eye'></i>
                </button>
            """
        else:
            preview_icon = ""

        if emp.salary:
            salary_icon = f"""
                <a class='btn btn-sm btn-primary' href='/salary-slip/{emp.id}'>
                    <i class='fa fa-download'></i>
                </a>
            """
        else:
            salary_icon = ""

        if role == 'Employee':
            status_icon = ""
            edit_icon = ""
        else:
            edit_icon ="<a class='btn btn-sm btn-primary' href='/employee/edit/{emp.id}'><i class='fa fa-edit' ></i> </a>"
            status_icon = "<button class='btn btn-sm btn-warning updateStatus' data-id='{emp.id}'><i class='fa fa-refresh' style='color:{icon_color};'></i></button>"


        rows.append({
            "id": emp.id,
            "full_name": usr.full_name,
            "email": usr.email,
            "phone": emp.phone,
            "department": emp.department,
            "designation": emp.designation,
            "salary": str(emp.salary),
            "hire_date": emp.hire_date.strftime("%Y-%m-%d"),
            "salary_slip": {salary_icon},
            "action": f"""
            {edit_icon}
            &nbsp;
            {status_icon}
            &nbsp;
            <a class='btn btn-sm btn-primary' href='/employee/upload_ids/{emp.id}'>
                <i class='fa fa-upload' ></i>
            </a>&nbsp;            {preview_icon}
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

@router.get("/employee/upload_ids/{emp_id}")
async def edit_ids_page(emp_id: int, request: Request, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    error = request.query_params.get("error")
    success = request.query_params.get("success")
    if not emp:
        return templates.TemplateResponse("404.html", {"request": request})

    return templates.TemplateResponse("upload_ids.html", { "request": request, **static_paths, "emp": emp,"error": error,"success": success })


@router.post("/employee/update_id_proof")
async def update_id_proof(employee_id: int = Form(...),
    upload_file: UploadFile = Form(...),
    db: Session = Depends(get_db)):

    dest_folder  = "static/uploads/idproofs"
    os.makedirs(dest_folder , exist_ok=True)

    content_type = upload_file.content_type
    if content_type not in ALLOWED_CONTENT_TYPES:
        #raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")
        return RedirectResponse(url=f"/employee/upload_ids/{employee_id}?error=Unsupported file type: {content_type}",status_code=303)

    # generate unique filename, keep original extension
    ext = os.path.splitext(upload_file.filename)[1].lower()
    if not ext:
        # try guess from content_type
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "application/pdf": ".pdf"
        }
        ext = ext_map.get(content_type, "")

    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(dest_folder, safe_name)

    # stream read/write and check size
    total = 0
    CHUNK = 1024 * 64
    try:
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = await upload_file.read(CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(dest_path)
                    #raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE} bytes allowed.")
                    return RedirectResponse(url=f"/employee/upload_ids/{employee_id}?error=File too large. Max {MAX_FILE_SIZE} bytes allowed.",status_code=303)
                buffer.write(chunk)
    finally:
        await upload_file.close()

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        #raise HTTPException(status_code=404, detail="Employee not found")
        return RedirectResponse(url=f"/employee/upload_ids/{employee_id}?error=Employee not found.",status_code=303)

    employee.id_proof = safe_name
    db.commit()

    return RedirectResponse(url=f"/employee/upload_ids/{employee_id}?success=ID proof uploaded & updated successfully.",status_code=200)
    


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
async def add_employee(request: Request, message: str = None,user=Depends(require_roles("Admin", "Super Admin"))):
    if request.session.get("user_id"):
        error = request.query_params.get("error")
        success = request.query_params.get("success")
        return templates.TemplateResponse("add_employee.html", {"request": request,**static_paths,"quote": quote,"author": author,"error": error,"success": success})
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
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        url = "/add_employee?error=Already Registered!"
        return RedirectResponse(url=url, status_code=303) 
            
    hashed_pw = hash_password(dob)
    new_user = User(full_name=full_name, email=email, password=hashed_pw, role='Employee')
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    user_id = new_user.id
    
    new_employee = Employee(phone=mobile, department=dept, designation=designation, salary=salary, hire_date=joining_date,dob=dob, user_id=user_id)
    db.add(new_employee)     
    db.commit()  

    create_audit_log(
            db=db,
            user_id=request.session.get("user_id"),
            action="CREATE",
            module="EMPLOYEE",
            record_id = new_employee.id,
            old_data=None,
            new_data={"employee_id": new_employee.id, "name": new_user.full_name},
            request=request
        )
                
    db.refresh(new_employee) 

    url = "/add_employee?message=Employee%20added%20successfully!"
    return RedirectResponse(url=url, status_code=303) 
    #return templates.TemplateResponse("add_employee.html", {"request": request, **static_paths,"message": "Employeem added successful!"})


@router.get("/user/edit/{user_id}")
async def edit_user_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return templates.TemplateResponse("404.html", {"request": request})

    return templates.TemplateResponse("edit_user.html", { "request": request, **static_paths, "user": user })

@router.post("/user/update")
async def employee_update(
    id: int = Form(...),
    full_name: str = Form(...),
    email_id: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.id == id).first()

    if not user:
        return {"success": False, "message": "User not found"}

    # Update employee
    user.full_name = full_name
    user.email = email_id
    user.role = role


    db.commit()
    
    return RedirectResponse("/users", status_code=302)

@router.get("/add_user")
async def add_user(request: Request, message: str = None,user=Depends(require_roles("Admin", "Super Admin"))):
    if request.session.get("user_id"):
        return templates.TemplateResponse("add_user.html", {"request": request,**static_paths,"message": message,})
    return templates.TemplateResponse("login.html", {"request": request,**static_paths,"status":400})


@router.get("/salary-slip/{employee_id}")
def salary_slip(employee_id: int, db: Session = Depends(get_db)):
    result = (db.query(Employee, User).join(User, Employee.user_id == User.id).filter(Employee.id == employee_id).first())

    if not result:
        raise HTTPException(404, "Employee not found")
    
    emp, user = result

    if emp.salary is None:
        raise HTTPException(400, "Salary not set for this employee")

    breakup = breakup_salary(Decimal(emp.salary))
    pdf = generate_pdf(emp,user, breakup)

    headers = {
        "Content-Disposition": f'attachment; filename="salary_slip_{user.full_name}.pdf"'
    }
    return StreamingResponse(pdf, media_type="application/pdf", headers=headers)

@router.get("/hr-chat")
def hr_chat_page(request: Request):
    if request.session.get("user_id"):
        return templates.TemplateResponse("hr_chat.html", {"request": request,**static_paths})
    return templates.TemplateResponse("login.html", {"request": request,**static_paths,"status":400})

@router.post("/chat/")
def chat_with_hr(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # Fetch employees from DB
        employees = get_all_employees(db)  # list of dicts with full_name, designation, etc.

        # Convert employee data to readable text
        employee_text = "\n".join(
            [f"{e['full_name']} is a {e['designation']} in {e['department']} with salary {e['salary']}" 
             for e in employees]
        )

        prompt = f"Here is the employee data:\n{employee_text}\n\nAnswer the following question based on this data: {request.question}"

        answer = ask_chatgpt(prompt)
        return {"answer": answer}

    except RateLimitError:
        return {"answer": "Sorry, OpenAI API quota exceeded. Please try again later."}
    except OpenAIError as e:
        return {"answer": f"OpenAI API error: {str(e)}"}
    except Exception as e:
        return {"answer": f"Unexpected error: {str(e)}"}