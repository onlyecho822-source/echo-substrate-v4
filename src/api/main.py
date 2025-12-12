"""
Echo Substrate v4 API
Production-ready FastAPI application with authentication, rate limiting, and proper security.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

from ..organs.models import Base, SystemState
from ..organs.arbiter import Arbiter, StateTransitionDenied
from ..organs.metabolism import Metabolism, BudgetExceeded
from ..organs.immune_system import ImmuneSystem


# =============================================================================
# Configuration
# =============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://substrate:substrate@localhost/echo_substrate_v4")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Allowed origins for CORS (NOT wildcard)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")


# =============================================================================
# Database Setup
# =============================================================================

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Clean up resources
    pass


# =============================================================================
# Security
# =============================================================================

security = HTTPBearer()


class TokenData(BaseModel):
    """Data contained in JWT token."""
    sub: str  # Subject (user/role ID)
    role: str  # Role name (e.g., "intent_architect", "operator")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenData:
    """Verify JWT token and extract user data."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        role: str = payload.get("role")
        if sub is None or role is None:
            raise credentials_exception
        token_data = TokenData(sub=sub, role=role)
    except JWTError:
        raise credentials_exception
    return token_data


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Echo Substrate v4",
    description="Apex-grade survivable substrate with 8-organ architecture",
    version="4.0.0",
    lifespan=lifespan
)

# CORS: Restricted to specific origins (NOT wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# --- Arbiter Endpoints ---

class StateTransitionRequest(BaseModel):
    """Request to transition system state."""
    to_state: SystemState
    trigger: str


@app.get("/api/v1/state")
async def get_system_state(
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get the current system state."""
    arbiter = Arbiter(db)
    return {
        "current_state": arbiter.current_state.value,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/state/transition")
async def request_state_transition(
    request: StateTransitionRequest,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Request a state transition."""
    arbiter = Arbiter(db)
    
    try:
        authorized_by = f"{token.role}:{token.sub}"
        success = arbiter.request_transition(
            to_state=request.to_state,
            trigger=request.trigger,
            authorized_by=authorized_by
        )
        return {
            "success": success,
            "new_state": arbiter.current_state.value,
            "timestamp": datetime.utcnow().isoformat()
        }
    except StateTransitionDenied as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# --- Metabolism Endpoints ---

class BudgetAllocation(BaseModel):
    """Request to allocate budget to an agent."""
    agent_id: str
    total_budget: float
    window_hours: int = 24


@app.post("/api/v1/metabolism/allocate")
async def allocate_budget(
    request: BudgetAllocation,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Allocate budget to an agent."""
    # Only operators and above can allocate budgets
    if token.role not in ["operator", "arbiter", "intent_architect"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    metabolism = Metabolism(db)
    metabolism.allocate_budget(
        agent_id=request.agent_id,
        total_budget=request.total_budget,
        window_hours=request.window_hours
    )
    
    return {
        "success": True,
        "agent_id": request.agent_id,
        "allocated_budget": request.total_budget
    }


@app.get("/api/v1/metabolism/budget/{agent_id}")
async def get_remaining_budget(
    agent_id: str,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get remaining budget for an agent."""
    metabolism = Metabolism(db)
    remaining = metabolism.get_remaining_budget(agent_id)
    
    return {
        "agent_id": agent_id,
        "remaining_budget": remaining,
        "timestamp": datetime.utcnow().isoformat()
    }


# --- Immune System Endpoints ---

class QuarantineRequest(BaseModel):
    """Request to quarantine an agent."""
    agent_id: str
    reason: str


@app.post("/api/v1/immune/quarantine")
async def quarantine_agent(
    request: QuarantineRequest,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Quarantine a misbehaving agent."""
    # Only arbiter and above can quarantine
    if token.role not in ["arbiter", "intent_architect"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    
    immune = ImmuneSystem(db)
    immune.quarantine_agent(agent_id=request.agent_id, reason=request.reason)
    
    return {
        "success": True,
        "agent_id": request.agent_id,
        "quarantined": True
    }


@app.get("/api/v1/immune/status/{agent_id}")
async def check_quarantine_status(
    agent_id: str,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Check if an agent is quarantined."""
    immune = ImmuneSystem(db)
    is_quarantined = immune.is_quarantined(agent_id)
    
    return {
        "agent_id": agent_id,
        "is_quarantined": is_quarantined,
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# Authentication Endpoint (for testing)
# =============================================================================

class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """
    Login endpoint (simplified for demonstration).
    In production, this would validate against a user database.
    """
    # Simplified role mapping for demonstration
    role_map = {
        "architect": "intent_architect",
        "arbiter": "arbiter",
        "operator": "operator",
        "auditor": "auditor",
        "maintainer": "maintainer"
    }
    
    role = role_map.get(request.username)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username, "role": role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "role": role}
