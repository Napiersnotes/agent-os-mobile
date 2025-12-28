import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import logging
from dataclasses import dataclass, field
import hashlib
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.models import Task, Agent, TaskResult, UserSession
from ..memory.vector_store import VectorMemory
from ..agents.manager import AgentManager
from ..utils.security import SecurityManager
from ..utils.cache import RedisCache

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TaskRequest:
    user_id: str
    input_text: str
    priority: TaskPriority = TaskPriority.MEDIUM
    attachments: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    device_info: Dict[str, Any] = field(default_factory=dict)

class AgentOrchestrator:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.agent_manager = AgentManager()
        self.memory = VectorMemory()
        self.security = SecurityManager()
        self.cache = RedisCache()
        
        self.task_queue = asyncio.Queue()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Performance tracking
        self.metrics = {
            'tasks_processed': 0,
            'avg_processing_time': 0.0,
            'success_rate': 1.0
        }
    
    async def initialize(self):
        """Initialize orchestrator components"""
        await self.memory.initialize()
        await self.cache.initialize()
        await self.agent_manager.initialize()
        
        # Start background processor
        asyncio.create_task(self._process_queue())
        logger.info("AgentOrchestrator initialized")
    
    async def submit_task(self, task_request: TaskRequest) -> str:
        """Submit a new task from mobile/web interface"""
        
        # Validate and sanitize input
        sanitized_input = await self.security.sanitize_input(task_request.input_text)
        
        # Check for similar tasks in cache
        task_hash = hashlib.md5(sanitized_input.encode()).hexdigest()
        cached_result = await self.cache.get(f"task:{task_hash}")
        
        if cached_result:
            logger.info(f"Returning cached result for task hash: {task_hash}")
            return await self._create_cached_task(task_request, cached_result)
        
        # Create new task in database
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            user_id=task_request.user_id,
            input_text=sanitized_input,
            priority=task_request.priority.value,
            status=TaskStatus.PENDING.value,
            metadata=json.dumps(task_request.metadata),
            device_info=json.dumps(task_request.device_info),
            created_at=datetime.utcnow()
        )
        
        self.db.add(task)
        await self.db.commit()
        
        # Add to processing queue
        await self.task_queue.put(task_id)
        
        logger.info(f"Task submitted: {task_id} by user {task_request.user_id}")
        return task_id
    
    async def get_task_status(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """Get task status and results"""
        # Check cache first
        cached = await self.cache.get(f"task_status:{task_id}")
        if cached:
            return cached
        
        # Query database
        result = await self.db.execute(
            select(Task, TaskResult).outerjoin(
                TaskResult, Task.id == TaskResult.task_id
            ).where(Task.id == task_id, Task.user_id == user_id)
        )
        
        task, task_result = result.first()
        
        if not task:
            raise ValueError("Task not found")
        
        response = {
            'task_id': task.id,
            'status': task.status,
            'input': task.input_text,
            'priority': task.priority,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat() if task.updated_at else None
        }
        
        if task_result:
            response.update({
                'result': task_result.result,
                'processing_time': task_result.processing_time,
                'agent_used': task_result.agent_used,
                'completed_at': task_result.completed_at.isoformat() if task_result.completed_at else None
            })
        
        # Cache for 30 seconds
        await self.cache.set(f"task_status:{task_id}", response, ttl=30)
        
        return response
    
    async def _process_queue(self):
        """Background task processor"""
        while True:
            try:
                task_id = await self.task_queue.get()
                
                # Process task
                task = await self._get_task(task_id)
                if task:
                    # Create async task for processing
                    process_task = asyncio.create_task(
                        self._process_single_task(task)
                    )
                    self.active_tasks[task_id] = process_task
                    
                    # Clean up completed tasks
                    self._cleanup_completed_tasks()
                
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_single_task(self, task: Task):
        """Process a single task with agents"""
        start_time = datetime.utcnow()
        
        try:
            # Update task status
            task.status = TaskStatus.PROCESSING.value
            task.updated_at = datetime.utcnow()
            await self.db.commit()
            
            # Analyze task complexity
            complexity = await self._analyze_complexity(task.input_text)
            
            # Select appropriate agent(s)
            agents = await self._select_agents(task, complexity)
            
            # Process with selected agents
            results = []
            for agent in agents:
                agent_result = await agent.process(task.input_text, task.metadata)
                results.append(agent_result)
            
            # Aggregate results
            final_result = await self._aggregate_results(results)
            
            # Store result
            task_result = TaskResult(
                task_id=task.id,
                result=json.dumps(final_result),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                agent_used=','.join([a.name for a in agents]),
                completed_at=datetime.utcnow()
            )
            
            self.db.add(task_result)
            
            # Update task status
            task.status = TaskStatus.COMPLETED.value
            task.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Cache the result
            task_hash = hashlib.md5(task.input_text.encode()).hexdigest()
            await self.cache.set(
                f"task:{task_hash}",
                final_result,
                ttl=3600  # Cache for 1 hour
            )
            
            # Update metrics
            self._update_metrics(success=True, processing_time=task_result.processing_time)
            
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.status = TaskStatus.FAILED.value
            task.updated_at = datetime.utcnow()
            await self.db.commit()
            
            self._update_metrics(success=False)
    
    async def _analyze_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze task complexity"""
        # Simple heuristic - can be enhanced with ML
        word_count = len(text.split())
        sentences = len([s for s in text.split('.') if s.strip()])
        
        if word_count < 20:
            return {'level': 'simple', 'agents_needed': 1}
        elif word_count < 100:
            return {'level': 'medium', 'agents_needed': 2}
        else:
            return {'level': 'complex', 'agents_needed': 3}
    
    async def _select_agents(self, task: Task, complexity: Dict) -> List:
        """Select appropriate agents for the task"""
        agents = []
        
        # Load available agents
        available_agents = await self.agent_manager.get_available_agents()
        
        # Simple rule-based selection (can be ML-based)
        if 'research' in task.input_text.lower():
            agents.append(available_agents.get('researcher'))
        if 'analyze' in task.input_text.lower() or 'data' in task.input_text.lower():
            agents.append(available_agents.get('analyst'))
        if 'write' in task.input_text.lower() or 'create' in task.input_text.lower():
            agents.append(available_agents.get('writer'))
        
        # Add general purpose agent if no specific agents found
        if not agents:
            agents.append(available_agents.get('general'))
        
        # Limit by complexity
        agents = agents[:complexity['agents_needed']]
        
        return [a for a in agents if a is not None]
    
    async def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results from multiple agents"""
        if len(results) == 1:
            return results[0]
        
        # Simple merging for now
        aggregated = {
            'summary': '',
            'details': [],
            'sources': [],
            'confidence': 0.0
        }
        
        for result in results:
            if 'summary' in result:
                aggregated['summary'] += result['summary'] + '\n\n'
            if 'details' in result:
                aggregated['details'].extend(result['details'])
            if 'sources' in result:
                aggregated['sources'].extend(result['sources'])
            if 'confidence' in result:
                aggregated['confidence'] = max(aggregated['confidence'], result['confidence'])
        
        # Average confidence if multiple agents
        aggregated['confidence'] = aggregated['confidence'] / len(results)
        
        return aggregated
    
    async def _create_cached_task(self, task_request: TaskRequest, cached_result: Dict) -> str:
        """Create task record for cached result"""
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            user_id=task_request.user_id,
            input_text=task_request.input_text,
            priority=task_request.priority.value,
            status=TaskStatus.COMPLETED.value,
            metadata=json.dumps(task_request.metadata),
            device_info=json.dumps(task_request.device_info),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        task_result = TaskResult(
            task_id=task_id,
            result=json.dumps(cached_result),
            processing_time=0.1,  # Almost instant for cached
            agent_used='cached',
            completed_at=datetime.utcnow()
        )
        
        self.db.add(task)
        self.db.add(task_result)
        await self.db.commit()
        
        return task_id
    
    async def _get_task(self, task_id: str) -> Optional[Task]:
        """Get task from database"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    def _update_metrics(self, success: bool, processing_time: float = 0):
        """Update performance metrics"""
        self.metrics['tasks_processed'] += 1
        
        if success:
            # Update average processing time (EMA)
            old_avg = self.metrics['avg_processing_time']
            self.metrics['avg_processing_time'] = old_avg * 0.9 + processing_time * 0.1
            
            # Update success rate
            total = self.metrics['tasks_processed']
            current_rate = self.metrics['success_rate']
            self.metrics['success_rate'] = (current_rate * (total - 1) + 1) / total
        else:
            total = self.metrics['tasks_processed']
            current_rate = self.metrics['success_rate']
            self.metrics['success_rate'] = current_rate * (total - 1) / total
    
    def _cleanup_completed_tasks(self):
        """Clean up completed tasks from active tasks dict"""
        to_remove = []
        for task_id, task in self.active_tasks.items():
            if task.done():
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        return {
            **self.metrics,
            'queue_size': self.task_queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'memory_usage': await self.memory.get_stats(),
            'cache_hit_rate': await self.cache.get_hit_rate(),
            'agents_available': len(await self.agent_manager.get_available_agents())
        }
    
    async def cancel_task(self, task_id: str, user_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            
            # Update task status
            task = await self._get_task(task_id)
            if task and task.user_id == user_id:
                task.status = TaskStatus.CANCELLED.value
                task.updated_at = datetime.utcnow()
                await self.db.commit()
                return True
        
        return False
