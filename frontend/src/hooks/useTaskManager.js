// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';

// WebSocket connection status
const CONNECTION_STATUS = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error'
};

const useTaskManager = () => {
  const { token, isLoggedIn } = useAuth();
  const { showToast } = useToast();
  const [tasks, setTasks] = useState({});
  const [connectionStatus, setConnectionStatus] = useState(CONNECTION_STATUS.DISCONNECTED);
  
  // WebSocket reference
  const wsRef = useRef(null);
  
  // Keep track of reconnection attempts
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectTimeout = useRef(null);
  
  // Setup ping interval for keepalive
  const pingInterval = useRef(null);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!token || !isLoggedIn) return;
    
    try {
      // Close existing connection if open
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        wsRef.current.close();
      }
      
      setConnectionStatus(CONNECTION_STATUS.CONNECTING);
      
      // Create new WebSocket connection
      wsRef.current = new WebSocket(`ws://localhost:8000/ws/tasks?token=${token}`);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus(CONNECTION_STATUS.CONNECTED);
        reconnectAttempts.current = 0; // Reset reconnect attempts on successful connection
        
        // Setup ping interval (every 30 seconds)
        pingInterval.current = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: 'ping',
              time: Date.now()
            }));
          }
        }, 30000);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'task_update':
              handleTaskUpdate(data.task);
              break;
            case 'error':
              console.error('WebSocket error:', data.detail);
              showToast(data.detail, 'error');
              break;
            case 'pong':
              // Optional: Calculate ping
              break;
            default:
              console.log('Received unknown message type:', data.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnectionStatus(CONNECTION_STATUS.DISCONNECTED);
        
        // Clear ping interval
        if (pingInterval.current) {
          clearInterval(pingInterval.current);
          pingInterval.current = null;
        }
        
        // Reconnect logic
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * (2 ** reconnectAttempts.current), 30000); // Exponential backoff, max 30s
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setConnectionStatus(CONNECTION_STATUS.ERROR);
          showToast('Failed to connect to server after multiple attempts', 'error');
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus(CONNECTION_STATUS.ERROR);
      };
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus(CONNECTION_STATUS.ERROR);
      showToast('Failed to connect to server', 'error');
    }
  }, [token, isLoggedIn, showToast]);
  
  // Handle task update
  const handleTaskUpdate = useCallback((task) => {
    setTasks((prevTasks) => ({
      ...prevTasks,
      [task.id]: task
    }));
    
    // Optionally show notifications for important status changes
    if (task.status === 'completed') {
      showToast(`Task completed: ${task.description}`, 'success');
    } else if (task.status === 'failed') {
      showToast(`Task failed: ${task.description}${task.error ? ` (${task.error})` : ''}`, 'error');
    }
  }, [showToast]);
  
  // Cancel a task
  const cancelTask = useCallback((taskId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && tasks[taskId]) {
      wsRef.current.send(JSON.stringify({
        type: 'cancel_task',
        task_id: taskId
      }));
      return true;
    }
    return false;
  }, [tasks]);
  
  // Connect when authenticated
  useEffect(() => {
    if (isLoggedIn && token) {
      connect();
    } else {
      // Clean up connection when logged out
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
        pingInterval.current = null;
      }
      
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      
      setConnectionStatus(CONNECTION_STATUS.DISCONNECTED);
      setTasks({});
    }
    
    return () => {
      // Clean up on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }
      
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
      
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, [isLoggedIn, token, connect]);
  
  // Get running tasks
  const getRunningTasks = useCallback(() => {
    return Object.values(tasks).filter(task => ['running'].includes(task.status));
  }, [tasks]);
  
  // Get recent tasks (completed, failed, cancelled in the last hour)
  const getRecentTasks = useCallback((limit = 5) => {
    const oneHourAgo = new Date();
    oneHourAgo.setHours(oneHourAgo.getHours() - 1);
    
    return Object.values(tasks)
      .filter(task => ['completed', 'failed', 'cancelled'].includes(task.status) && new Date(task.updated_at) > oneHourAgo)
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      .slice(0, limit);
  }, [tasks]);
  
  return {
    tasks,
    runningTasks: getRunningTasks(),
    recentTasks: getRecentTasks(),
    connectionStatus,
    cancelTask,
    isConnected: connectionStatus === CONNECTION_STATUS.CONNECTED
  };
};

export default useTaskManager;