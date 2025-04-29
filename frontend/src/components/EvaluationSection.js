// Last reviewed: 2025-04-29 07:31:24 UTC (User: TeeksssLogin)
import React, { useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import useTaskManager from '../hooks/useTaskManager';
import EvaluationChart from './EvaluationChart';
import Spinner from './ui/Spinner';
import './EvaluationSection.css';

const EvaluationSection = () => {
  const [evaluationResults, setEvaluationResults] = useState(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  
  const { isLoggedIn, isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest } = useApi();
  const { runningTasks } = useTaskManager();
  
  // Check if there's any running evaluation task
  const evaluationTask = runningTasks.find(task => task.type === 'evaluate');
  
  const handleEvaluate = useCallback(async () => {
    setIsEvaluating(true);
    
    try {
      const data = await apiRequest("/evaluate", { method: "POST" });
      setEvaluationResults(data.results);
      showToast('Değerlendirme tamamlandı!', 'success');
    } catch (error) {
      showToast(`Değerlendirme hatası: ${error.message}`, 'error');
    } finally {
      setIsEvaluating(false);
    }
  }, [apiRequest, showToast]);
  
  if (!isLoggedIn || !isAdmin) {
    return null;
  }
  
  const isBusy = isEvaluating || !!evaluationTask;
  
  return (
    <section className="evaluation-section card">
      <h2>Değerlendirme</h2>
      
      <div className="evaluation-description">
        <p>
          Bu bölüm, RAG pipeline'ının performansını değerlendirmek için çeşitli metrikler kullanır.
          Değerlendirme süreci, mevcut veri kaynakları üzerinde çalışır ve sonuçları görselleştirir.
        </p>
      </div>
      
      <button
        onClick={handleEvaluate}
        disabled={isBusy}
        className="action-button"
      >
        {isBusy ? (
          <><Spinner size="small" /> Değerlendiriliyor...</>
        ) : (
          "RAG Pipeline'ını Değerlendir"
        )}
      </button>
      
      {evaluationTask && (
        <div className="evaluation-progress">
          <div className="progress-bar" style={{ width: `${evaluationTask.progress}%` }}></div>
          <div className="progress-text">Değerlendir