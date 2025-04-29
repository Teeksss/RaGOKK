# Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
import asyncio
import json
import uuid
from datetime import datetime
import time

from ..auth import get_current_user_ws
from ..db.database import get_db
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        # user_id -> set of active WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # task_id -> task info
        self.tasks: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Send existing tasks for this user
        user_tasks = [task for task in self.tasks.values() if task.get('user_id') == user_id]
        for task in user_tasks:
            await websocket.send_text(json.dumps({
                'type': 'task_update',
                'task': task
            }))
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")
    
    def create_task(self, user_id: int, task_type: str, description: str) -> str:
        """Create a new background task and notify connected clients"""
        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'user_id': user_id,
            'type': task_type,
            'description': description,
            'status': 'running',
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'error': None,
            'result': None
        }
        self.tasks[task_id] = task
        
        # Async broadcast
        asyncio.create_task(self.broadcast_task_update(user_id, task))
        return task_id
    
    async def update_task(self, task_id: str, **updates):
        """Update a task and notify connected clients"""
        if task_id not in self.tasks:
            logger.error(f"Attempted to update unknown task: {task_id}")
            return False
        
        task = self.tasks[task_id]
        for key, value in updates.items():
            if key in task:
                task[key] = value
        
        # Always update timestamp
        task['updated_at'] = datetime.utcnow().isoformat()
        
        # If status is terminal, add completed_at timestamp
        if updates.get('status') in ['completed', 'failed', 'cancelled']:
            task['completed_at'] = datetime.utcnow().isoformat()
        
        # Broadcast update
        await self.broadcast_task_update(task['user_id'], task)
        return True
    
    async def broadcast_task_update(self, user_id: int, task: Dict):
        """Broadcast task update to all connections for a user"""
        if user_id not in self.active_connections:
            return
        
        message = json.dumps({
            'type': 'task_update',
            'task': task
        })
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[user_id].copy()
        failed_connections = set()
        
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                failed_connections.add(connection)
        
        # Remove failed connections
        for conn in failed_connections:
            self.active_connections[user_id].discard(conn)

manager = ConnectionManager()

async def get_ws_manager():
    return manager

# Function to update task in background
async def run_background_task(task_id: str, user_id: int, func, **kwargs):
    """
    Generic function to run a background task with progress updates.
    
    Args:
        task_id: The ID of the task
        user_id: User ID
        func: Async function to run
        **kwargs: Arguments to pass to func
    """
    try:
        # Start the task
        result = await func(
            task_id=task_id,
            progress_callback=lambda p, status=None: 
                asyncio.create_task(manager.update_task(
                    task_id, 
                    progress=p,
                    status=status if status else 'running'
                )),
            **kwargs
        )
        
        # Task completed successfully
        await manager.update_task(
            task_id,
            status='completed',
            progress=100,
            result=result
        )
        logger.info(f"Background task {task_id} completed")
        
    except Exception as e:
        # Task failed
        logger.error(f"Background task {task_id} failed: {e}", exc_info=True)
        await manager.update_task(
            task_id,
            status='failed',
            error=str(e)
        )