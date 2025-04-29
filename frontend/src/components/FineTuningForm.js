// Last reviewed: 2025-04-29 08:20:31 UTC (User: Teekssstüm)
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import useApi from '../hooks/useApi';
import useTaskManager from '../hooks/useTaskManager';
import Spinner from './ui/Spinner';
import './FineTuningForm.css';

const FineTuningForm = () => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();
  const { apiRequest, isLoading } = useApi();
  const { runningTasks } = useTaskManager();
  
  // Form state
  const [modelName, setModelName] = useState('meta-llama/Llama-2-7b-hf');
  const [outputModelName, setOutputModelName] = useState('');
  const [epochs, setEpochs] = useState(3);
  const [useLora, setUseLora] = useState(true);
  const [use8bit, setUse8bit] = useState(false);
  const [examples, setExamples] = useState([{ question: '', context: '', answer: '' }]);
  const [learningRate, setLearningRate] = useState(0.00003); // 3e-5
  const [batchSize, setBatchSize] = useState(8);
  
  // İşlemde olan fine-tune task'ini bul
  const fineTuningTask = runningTasks.find(task => task.type === 'fine-tune');
  
  // Form validation
  const [errors, setErrors] = useState({});
  
  const validateForm = () => {
    const newErrors = {};
    
    if (!modelName.trim()) {
      newErrors.modelName = 'Model adı gerekli';
    }
    
    let hasExampleError = false;
    examples.forEach((example, index) => {
      if (!example.question.trim()) {
        newErrors[`question_${index}`] = 'Soru gerekli';
        hasExampleError = true;
      }
      if (!example.answer.trim()) {
        newErrors[`answer_${index}`] = 'Cevap gerekli';
        hasExampleError = true;
      }
    });
    
    if (hasExampleError) {
      newErrors.examples = 'Tüm örnek soruların ve cevapların doldurulması gerekli';
    }
    
    if (examples.length === 0) {
      newErrors.examples = 'En az bir örnek gerekli';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Handle example changes
  const handleExampleChange = (index, field, value) => {
    const newExamples = [...examples];
    newExamples[index] = { ...newExamples[index], [field]: value };
    setExamples(newExamples);
    
    // Clear field error if value is provided
    if (value.trim() && errors[`${field}_${index}`]) {
      const newErrors = { ...errors };
      delete newErrors[`${field}_${index}`];
      setErrors(newErrors);
    }
  };
  
  // Add new example
  const addExample = () => {
    setExamples([...examples, { question: '', context: '', answer: '' }]);
  };
  
  // Remove example
  const removeExample = (index) => {
    if (examples.length > 1) {
      const newExamples = [...examples];
      newExamples.splice(index, 1);
      setExamples(newExamples);
    } else {
      showToast('En az bir örnek gerekli', 'warning');
    }
  };
  
  // Submit form
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      showToast('Lütfen formu kontrol edin', 'error');
      return;
    }
    
    try {
      const response = await apiRequest('/api/fine-tune', {
        method: 'POST',
        body: JSON.stringify({
          model_name: modelName,
          output_model_name: outputModelName || undefined,
          epochs: Number(epochs),
          use_lora: useLora,
          use_8bit: use8bit,
          learning_rate: Number(learningRate),
          batch_size: Number(batchSize),
          examples: examples
        })
      });
      
      showToast('Fine-tuning başlatıldı! İlerlemeyi görevler panelinden takip edebilirsiniz.', 'success');
      
      // Form sıfırla
      setOutputModelName('');
      setExamples([{ question: '', context: '', answer: '' }]);
      
    } catch (error) {
      showToast(`Fine-tuning başlatılamadı: ${error.message}`, 'error');
    }
  };
  
  if (!isAdmin) {
    return null;
  }
  
  return (
    <div className="fine-tuning-container">
      <h2>Model Fine-Tuning</h2>
      
      {fineTuningTask ? (
        <div className="running-task-info">
          <h3>Fine-Tuning Sürüyor</h3>
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${fineTuningTask.progress}%` }}></div>
            <div className="progress-text">{fineTuningTask.progress}%</div>
          </div>
          <p><strong>Durum:</strong> {fineTuningTask.status || 'İşleniyor'}</p>
          <p><strong>Açıklama:</strong> {fineTuningTask.description}</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="fine-tuning-form">
          <div className="form-section">
            <h3>Model Yapılandırması</h3>
            
            <div className="form-group">
              <label htmlFor="modelName">Base Model Adı</label>
              <input 
                type="text"
                id="modelName"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className={errors.modelName ? 'error' : ''}
              />
              {errors.modelName && <div className="error-message">{errors.modelName}</div>}
              <div className="help-text">HuggingFace'deki model adı (örn: meta-llama/Llama-2-7b-hf)</div>
            </div>
            
            <div className="form-group">
              <label htmlFor="outputModelName">Çıktı Model Adı (Opsiyonel)</label>
              <input 
                type="text"
                id="outputModelName"
                value={outputModelName}
                onChange={(e) => setOutputModelName(e.target.value)}
              />
              <div className="help-text">Boş bırakılırsa otomatik isim atanır</div>
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="epochs">Epoch Sayısı</label>
                <input 
                  type="number"
                  id="epochs"
                  value={epochs}
                  onChange={(e) => setEpochs(e.target.value)}
                  min="1"
                  max="10"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="learningRate">Öğrenme Oranı</label>
                <input 
                  type="number"
                  id="learningRate"
                  value={learningRate}
                  onChange={(e) => setLearningRate(e.target.value)}
                  step="0.00001"
                  min="0.00001"
                  max="0.01"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="batchSize">Batch Size</label>
                <input 
                  type="number"
                  id="batchSize"
                  value={batchSize}
                  onChange={(e) => setBatchSize(e.target.value)}
                  min="1"
                  max="32"
                />
              </div>
            </div>
            
            <div className="form-row">
              <div className="checkbox-group">
                <label>
                  <input 
                    type="checkbox"
                    checked={useLora}
                    onChange={(e) => setUseLora(e.target.checked)}
                  />
                  LoRA Kullan (Daha az hafıza)
                </label>
              </div>
              
              <div className="checkbox-group">
                <label>
                  <input 
                    type="checkbox"
                    checked={use8bit}
                    onChange={(e) => setUse8bit(e.target.checked)}
                  />
                  8-bit Quantization (Daha az hafıza)
                </label>
              </div>
            </div>
          </div>
          
          <div className="form-section">
            <h3>Eğitim Örnekleri</h3>
            
            {errors.examples && <div className="error-message examples-error">{errors.examples}</div>}
            
            {examples.map((example, index) => (
              <div key={index} className="example-container">
                <div className="example-header">
                  <h4>Örnek #{index + 1}</h4>
                  <button 
                    type="button"
                    className="remove-example-button"
                    onClick={() => removeExample(index)}
                  >
                    Kaldır
                  </button>
                </div>
                
                <div className="form-group">
                  <label htmlFor={`question_${index}`}>Soru</label>
                  <input 
                    type="text"
                    id={`question_${index}`}
                    value={example.question}
                    onChange={(e) => handleExampleChange(index, 'question', e.target.value)}
                    className={errors[`question_${index}`] ? 'error