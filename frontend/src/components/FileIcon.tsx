// Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
import React from 'react';
import '../styles/FileIcon.css';

interface FileIconProps {
  fileType: string;
  size?: 'sm' | 'md' | 'lg';
}

export const FileIcon: React.FC<FileIconProps> = ({ fileType, size = 'md' }) => {
  const getFileIcon = (): { icon: string, color: string } => {
    const normalizedType = fileType?.toLowerCase();
    
    switch(normalizedType) {
      case 'pdf':
        return { icon: 'bi-file-earmark-pdf', color: '#e74c3c' };
        
      case 'docx':
      case 'doc':
        return { icon: 'bi-file-earmark-word', color: '#2980b9' };
        
      case 'txt':
      case 'text':
        return { icon: 'bi-file-earmark-text', color: '#7f8c8d' };
        
      case 'html':
      case 'htm':
        return { icon: 'bi-file-earmark-code', color: '#e67e22' };
        
      case 'xml':
        return { icon: 'bi-file-earmark-code', color: '#9b59b6' };
        
      case 'json':
        return { icon: 'bi-file-earmark-code', color: '#f39c12' };
        
      case 'csv':
        return { icon: 'bi-file-earmark-spreadsheet', color: '#27ae60' };
        
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'bmp':
      case 'svg':
        return { icon: 'bi-file-earmark-image', color: '#3498db' };
      
      default:
        return { icon: 'bi-file-earmark', color: '#95a5a6' };
    }
  };
  
  const { icon, color } = getFileIcon();
  
  const sizeClass = {
    sm: 'file-icon-sm',
    md: 'file-icon-md',
    lg: 'file-icon-lg'
  }[size];
  
  return (
    <div className={`file-icon ${sizeClass}`} style={{ backgroundColor: color }}>
      <i className={`bi ${icon}`}></i>
    </div>
  );
};