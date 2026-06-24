import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user_db import User

router = APIRouter()


def _hash(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


# ── Schemas ────────────────────────────────────────────────────────────────

class ManagerSummary(BaseModel):
    id: str
    name: str
    email: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "Learner"
    manager_id: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    manager_id: str | None


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/managers", response_model=list[ManagerSummary])
def list_managers(db: Session = Depends(get_db)):
    managers = db.query(User).filter(User.role == "Manager").order_by(User.name).all()
    return [ManagerSummary(id=m.id, name=m.name, email=m.email) for m in managers]


@router.post("/signup", response_model=UserProfile, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if payload.role not in ("Learner", "Manager", "Admin"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be Learner, Manager, or Admin.")
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")
    if payload.role == "Learner" and payload.manager_id:
        mgr = db.query(User).filter(User.id == payload.manager_id, User.role == "Manager").first()
        if not mgr:
            raise HTTPException(status_code=400, detail="Invalid manager_id: user not found or not a Manager.")

    user = User(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        role=payload.role,
        hashed_password=_hash(payload.password),
        manager_id=payload.manager_id if payload.role == "Learner" else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserProfile(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        manager_id=user.manager_id,
    )


@router.post("/login", response_model=UserProfile)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or user.hashed_password != _hash(payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return UserProfile(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        manager_id=user.manager_id,
    )
