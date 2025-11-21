from sqlalchemy import Column, Integer, String, Enum,text, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import enum

class UserRole(str, enum.Enum):
    Admin = "Admin"
    SuperAdmin = "Super Admin"
    Employee = "Employee"

class StatusEnum(str, enum.Enum):
    Y = "Y"
    N = "N"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(
    Enum(UserRole, values_callable=lambda enum: [e.value for e in enum], name="role", create_type=False),
    nullable=False,
    server_default="Super Admin"
)
    status = Column(String, default="Y")
    created_on = Column(String, server_default=text("CURRENT_DATE"),nullable=False)
    employees = relationship("Employee", back_populates="user")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    department = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    salary = Column(Numeric, nullable=False)
    hire_date = Column(Date, nullable=False)
    status = Column(Enum(StatusEnum, name="status_enum"), default=StatusEnum.Y)
    dob = Column(Date, nullable=False)

    # user_id is just an INTEGER column — NOT a foreign key
    user_id = Column( Integer, ForeignKey( "users.id", name="fk_user_employee", deferrable=True, initially="DEFERRED", use_alter=True ), nullable=False )
    user = relationship("User", back_populates="employees")
