from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = "postgresql://postgres:admin123@localhost:5432/emp_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_all_employees(db: Session):
    from models import Employee, User
    employees = db.query(Employee, User.full_name).join(User, Employee.user_id == User.id).all()
    
    result = []
    for e, full_name  in employees:
        result.append({
            "full_name": full_name,
            "designation": e.designation,
            "department": e.department,
            "salary": e.salary
        })
    return result
