from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import json
import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..core.orchestrator import AgentOrchestrator, TaskRequest, TaskPriority
from ..database.models import Base, User, Task, TaskResult
from ..utils.auth import AuthHandler, get_current_user
from ..utils.websocket import ConnectionManager
from ..config import settings

# Models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class TaskSubmit(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=5000)
    priority: str = "medium"
    attachments: List[Dict] = []
    metadata: Dict[str, Any] = {}
    device_info: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None

# FastAPI App
app = FastAPI(
    title="Agent OS API",
    description="Advanced Agent Operating System with Mobile Interface",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS for mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
auth_handler = AuthHandler()

# Database
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# WebSocket manager
ws_manager = ConnectionManager()

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_orchestrator(db: AsyncSession = Depends(get_db)):
    orchestrator = AgentOrchestrator(db)
    await orchestrator.initialize()
    return orchestrator

# Events
@app.on_event("startup")
async def startup_event():
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Agent OS started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    await engine.dispose()
    print("Agent OS stopped")

# Routes
@app.post("/api/register", response_model=Dict[str, str])
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register new user"""
    # Check if user exists
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    # Create user
    hashed_password = auth_handler.get_password_hash(user_data.password)
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        hashed_password=hashed_password,
        name=user_data.name,
        created_at=datetime.utcnow()
    )
    
    db.add(user)
    await db.commit()
    
    # Generate token
    token = auth_handler.encode_token(user.id)
    
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/login", response_model=Dict[str, str])
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """User login"""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not auth_handler.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token = auth_handler.encode_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskSubmit,
    current_user: Dict = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Submit a new task"""
    try:
        # Convert priority string to enum
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        
        priority = priority_map.get(task.priority.lower(), TaskPriority.MEDIUM)
        
        # Create task request
        task_request = TaskRequest(
            user_id=current_user["user_id"],
            input_text=task.input_text,
            priority=priority,
            attachments=task.attachments,
            metadata=task.metadata,
            device_info=task.device_info
        )
        
        # Submit to orchestrator
        task_id = await orchestrator.submit_task(task_request)
        
        # Estimate processing time based on complexity
        estimated_time = len(task.input_text.split()) * 0.1  # ~0.1 sec per word
        
        return TaskResponse(
            task_id=task_id,
            status="accepted",
            message="Task submitted for processing",
            estimated_time=min(int(estimated_time), 60)  # Max 60 seconds
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/tasks/{task_id}")
async def get_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get task status and results"""
    try:
        result = await orchestrator.get_task_status(task_id, current_user["user_id"])
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@app.get("/api/tasks")
async def list_tasks(
    skip: int = 0,
    limit: int = 20,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's tasks"""
    from sqlalchemy import select, desc
    
    result = await db.execute(
        select(Task)
        .where(Task.user_id == current_user["user_id"])
        .order_by(desc(Task.created_at))
        .offset(skip)
        .limit(limit)
    )
    
    tasks = result.scalars().all()
    
    return [{
        "id": task.id,
        "input": task.input_text[:100] + "..." if len(task.input_text) > 100 else task.input_text,
        "status": task.status,
        "priority": task.priority,
        "created_at": task.created_at.isoformat()
    } for task in tasks]

@app.delete("/api/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Cancel a task"""
    success = await orchestrator.cancel_task(task_id, current_user["user_id"])
    
    if success:
        return {"message": "Task cancelled successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to cancel task"
        )

@app.get("/api/system/metrics")
async def get_metrics(
    current_user: Dict = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get system metrics (admin only)"""
    # Check if user is admin (simplified)
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    metrics = await orchestrator.get_system_metrics()
    return metrics

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: str
):
    """WebSocket endpoint for real-time updates"""
    # Verify token
    try:
        payload = auth_handler.decode_token(token)
        user_id = payload.get("sub")
    except:
        await websocket.close(code=1008)
        return
    
    await ws_manager.connect(websocket, client_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Handle different message types
            message = json.loads(data)
            
            if message.get("type") == "subscribe_task":
                task_id = message.get("task_id")
                await ws_manager.subscribe_to_task(client_id, task_id)
                
                # Send initial task status
                async with AsyncSessionLocal() as session:
                    orchestrator = AgentOrchestrator(session)
                    await orchestrator.initialize()
                    
                    task_status = await orchestrator.get_task_status(task_id, user_id)
                    await ws_manager.send_personal_message(
                        json.dumps({
                            "type": "task_update",
                            "task_id": task_id,
                            "status": task_status
                        }),
                        websocket
                    )
            
            elif message.get("type") == "unsubscribe_task":
                task_id = message.get("task_id")
                await ws_manager.unsubscribe_from_task(client_id, task_id)
    
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "agent-os"
    }

# Mobile-optimized HTML interface
@app.get("/", response_class=HTMLResponse)
async def mobile_interface():
    """Mobile-optimized web interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Agent OS - Mobile</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                -webkit-tap-highlight-color: transparent;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: env(safe-area-inset-top) env(safe-area-inset-right) 
                         env(safe-area-inset-bottom) env(safe-area-inset-left);
            }
            
            .container {
                max-width: 100%;
                padding: 20px;
                padding-top: max(20px, env(safe-area-inset-top));
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
                color: white;
            }
            
            .header h1 {
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 8px;
            }
            
            .header p {
                font-size: 16px;
                opacity: 0.9;
            }
            
            .card {
                background: white;
                border-radius: 20px;
                padding: 24px;
                margin-bottom: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            }
            
            .input-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                font-weight: 600;
                margin-bottom: 8px;
                color: #333;
            }
            
            textarea {
                width: 100%;
                min-height: 120px;
                padding: 16px;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                font-size: 16px;
                font-family: inherit;
                resize: vertical;
                transition: border-color 0.3s;
            }
            
            textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .priority-selector {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
                margin: 15px 0;
            }
            
            .priority-btn {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                background: white;
                font-size: 14px;
                font-weight: 500;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                user-select: none;
            }
            
            .priority-btn.active {
                border-color: #667eea;
                background: #667eea;
                color: white;
            }
            
            .btn {
                width: 100%;
                padding: 18px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.3s, box-shadow 0.3s;
                touch-action: manipulation;
            }
            
            .btn:active {
                transform: scale(0.98);
            }
            
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .result-card {
                display: none;
            }
            
            .result-card.show {
                display: block;
                animation: slideUp 0.5s ease;
            }
            
            .result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .status-badge {
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }
            
            .status-pending { background: #ffd700; color: #333; }
            .status-processing { background: #4dabf7; color: white; }
            .status-completed { background: #40c057; color: white; }
            .status-failed { background: #fa5252; color: white; }
            
            .result-content {
                background: #f8f9fa;
                padding: 16px;
                border-radius: 10px;
                margin-top: 15px;
                white-space: pre-wrap;
                word-break: break-word;
            }
            
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            
            .spinner {
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .task-list {
                max-height: 300px;
                overflow-y: auto;
                -webkit-overflow-scrolling: touch;
            }
            
            .task-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .task-item:last-child {
                border-bottom: none;
            }
            
            .task-text {
                flex: 1;
                margin-right: 15px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            
            @media (max-width: 480px) {
                .container {
                    padding: 15px;
                }
                
                .card {
                    padding: 20px;
                }
                
                .header h1 {
                    font-size: 24px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Agent OS</h1>
                <p>AI-Powered Task Automation</p>
            </div>
            
            <div class="card">
                <div class="input-group">
                    <label for="taskInput">Enter your task:</label>
                    <textarea 
                        id="taskInput" 
                        placeholder="What would you like me to help you with? For example: 'Research AI trends for 2024' or 'Analyze this sales data...'"
                        maxlength="5000"
                    ></textarea>
                    <div style="text-align: right; font-size: 12px; color: #666; margin-top: 5px;">
                        <span id="charCount">0</span>/5000
                    </div>
                </div>
                
                <div class="input-group">
                    <label>Priority:</label>
                    <div class="priority-selector">
                        <div class="priority-btn active" data-priority="medium">Medium</div>
                        <div class="priority-btn" data-priority="low">Low</div>
                        <div class="priority-btn" data-priority="high">High</div>
                        <div class="priority-btn" data-priority="urgent">Urgent</div>
                    </div>
                </div>
                
                <button class="btn" id="submitBtn" onclick="submitTask()">
                    🚀 Process Task
                </button>
            </div>
            
            <div class="card result-card" id="resultCard">
                <div class="result-header">
                    <h3>Task Result</h3>
                    <div class="status-badge status-pending" id="statusBadge">Pending</div>
                </div>
                <div id="resultContent" class="result-content"></div>
            </div>
            
            <div class="card">
                <h3 style="margin-bottom: 15px;">Recent Tasks</h3>
                <div class="task-list" id="taskList">
                    <div class="loading" id="loadingTasks">
                        <div class="spinner"></div>
                        Loading tasks...
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Global variables
            let currentTaskId = null;
            let ws = null;
            let a
