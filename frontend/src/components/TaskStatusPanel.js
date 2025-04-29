// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React from 'react';
import useTaskManager from '../hooks/useTaskManager';
import Spinner from './ui/Spinner';
import './TaskStatusPanel.css';

const TaskStatusPanel = () => {
  const { runningTasks, recentTasks, connectionStatus, cancelTask } = useTaskManager();
  
  const formatTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString();
  };
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <Spinner size="small" />;
      case 'completed':
        return <span className="task-icon completed">✓</span>;
      case 'failed':
        return <span className="task-icon failed">✗</span>;
      case 'cancelled':
        return <span className="task-icon cancelled">⊘</span>;
      default:
        return null;
    }
  };
  
  const handleCancelTask = (taskId) => {
    if (window.confirm('Are you sure you want to cancel this task?')) {
      cancelTask(taskId);
    }
  };
  
  if (connectionStatus !== 'connected' && runningTasks.length === 0 && recentTasks.length === 0) {
    return null;
  }
  
  return (
    <div className="task-status-panel">
      <div className="task-status-header">
        <h3>Background Tasks</h3>
        <span className={`connection-status ${connectionStatus}`}>
          {connectionStatus === 'connected' ? 'Connected' : 
           connectionStatus === 'connecting' ? 'Connecting...' : 
           connectionStatus === 'error' ? 'Connection Error' : 'Disconnected'}
        </span>
      </div>
      
      {runningTasks.length > 0 && (
        <div className="task-section">
          <h4>Running Tasks</h4>
          <ul className="task-list">
            {runningTasks.map(task => (
              <li key={task.id} className="task-item running">
                <div className="task-header">
                  <div className="task-icon-wrapper">{getStatusIcon(task.status)}</div>
                  <div className="task-title">{task.description}</div>
                  <button 
                    className="cancel-button" 
                    onClick={() => handleCancelTask(task.id)}
                  >
                    Cancel
                  </button>
                </div>
                <div className="task-progress-container">
                  <div className="task-progress-bar" style={{ width: `${task.progress}%` }}></div>
                  <div className="task-progress-text">{task.progress}%</div>
                </div>
                <div className="task-details">
                  <span>Started at {formatTime(task.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {recentTasks.length > 0 && (
        <div className="task-section">
          <h4>Recent Tasks</h4>
          <ul className="task-list">
            {recentTasks.map(task => (
              <li key={task.id} className={`task-item ${task.status}`}>
                <div className="task-header">
                  <div className="task-icon-wrapper">{getStatusIcon(task.status)}</div>
                  <div className="task-title">{task.description}</div>
                </div>
                <div className="task-details">
                  <span>
                    {task.status === 'completed' ? 'Completed' : 
                     task.status === 'failed' ? 'Failed' : 'Cancelled'} at {formatTime(task.completed_at)}
                  </span>
                  {task.error && <div className="task-error">{task.error}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default TaskStatusPanel;