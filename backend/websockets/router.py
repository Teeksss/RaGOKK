# Last reviewed: 2025-04-29 08:20:31 UTC (User: Teekssstüm)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import json
from typing import Optional, List
import asyncio

from ..db.async_database import get_db
from ..auth import get_current_user_ws, UserInDB
from .background_tasks import manager, get_ws_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.websocket("/ws/tasks")
async def websocket_tasks(
    websocket: WebSocket, 
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ws_manager = Depends(get_ws_manager)
):
    """WebSocket connection for background task updates"""
    # Authenticate user from token
    try:
        user = await get_current_user_ws(token, db)
    except HTTPException as e:
        # Cannot raise HTTPException in WebSocket endpoint, so close with error
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Authentication failed"
        }))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect
    await ws_manager.connect(websocket, user.id)
    
    try:
        while True:
            # Wait for messages (heartbeats, commands)
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get('type')
                
                if message_type == 'ping':
                    # Heartbeat
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "time": message.get('time', 0)
                    }))
                elif message_type == 'cancel_task':
                    # Cancel task request
                    task_id = message.get('task_id')
                    if not task_id or task_id not in ws_manager.tasks:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "detail": "Invalid task ID"
                        }))
                        continue
                    
                    # Check if user owns the task
                    task = ws_manager.tasks[task_id]
                    if task.get('user_id') != user.id and 'admin' not in user.roles:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "detail": "You don't have permission to cancel this task"
                        }))
                        continue
                    
                    # Update task status
                    await ws_manager.update_task(task_id, status='cancelled')
                    await websocket.send_text(json.dumps({
                        "type": "task_cancelled",
                        "task_id": task_id
                    }))
                elif message_type == 'get_tasks':
                    # Return all tasks for this user
                    user_tasks = [task for task_id, task in ws_manager.tasks.items() 
                                if task.get('user_id') == user.id]
                    await websocket.send_text(json.dumps({
                        "type": "tasks_list",
                        "tasks": user_tasks
                    }))
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from WebSocket")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "Invalid message format"
                }))
            except Exception as e:
                logger.error(f"WebSocket message processing error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "Failed to process message"
                }))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user.id)