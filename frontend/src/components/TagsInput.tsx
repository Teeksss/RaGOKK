// Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
import React, { useState, useRef, KeyboardEvent } from 'react';
import { Badge, Form, FormControl } from 'react-bootstrap';
import '../styles/TagsInput.css';

interface TagsInputProps {
  tags: string[];
  setTags: React.Dispatch<React.SetStateAction<string[]>>;
  maxTags?: number;
  maxLength?: number;
  placeholder?: string;
  disabled?: boolean;
}

export const TagsInput: React.FC<TagsInputProps> = ({
  tags,
  setTags,
  maxTags = 10,
  maxLength = 50,
  placeholder = 'Etiket ekle...',
  disabled = false
}) => {
  const [input, setInput] = useState('');
  const [isActive, setIsActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Yeni etiket ekle
  const addTag = (tag: string) => {
    // Boş etiketleri eklemiyoruz
    tag = tag.trim().toLowerCase();
    if (tag.length === 0) return;
    
    // Çok uzun etiketleri kırp
    if (tag.length > maxLength) {
      tag = tag.substring(0, maxLength);
    }
    
    // Zaten eklenmişse veya maksimum etiket sayısına ulaşılmışsa ekleme
    if (tags.includes(tag) || tags.length >= maxTags) return;
    
    // Etiket ekle
    setTags([...tags, tag]);
    setInput('');
  };
  
  // Etiket sil
  const removeTag = (tagToRemove: string) => {
    if (disabled) return;
    setTags(tags.filter(tag => tag !== tagToRemove));
  };
  
  // Tuş olayları
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Enter tuşu (yeni etiket ekle)
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag(input);
    }
    // Backspace tuşu (son etiketi sil)
    else if (e.key === 'Backspace' && input === '' && tags.length > 0) {
      e.preventDefault();
      removeTag(tags[tags.length - 1]);
    }
    // Virgül (yeni etiket ekle)
    else if (e.key === ',') {
      e.preventDefault();
      addTag(input);
    }
  };
  
  // Konteynera tıklandığında input'a odaklan
  const handleContainerClick = () => {
    if (disabled) return;
    inputRef.current?.focus();
  };
  
  return (
    <div 
      className={`tags-input-container ${isActive ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
      onClick={handleContainerClick}
    >
      <div className="tags-list">
        {tags.map((tag, index) => (
          <Badge 
            key={index} 
            bg="primary" 
            className="tag-badge"
          >
            {tag}
            {!disabled && (
              <span 
                className="tag-remove" 
                onClick={(e) => {
                  e.stopPropagation();
                  removeTag(tag);
                }}
              >
                &times;
              </span>
            )}
          </Badge>
        ))}
        
        {!disabled && tags.length < maxTags && (
          <FormControl
            ref={inputRef}
            className="tag-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsActive(true)}
            onBlur={() => {
              setIsActive(false);
              // Input boşaltılırken son değeri etiket olarak ekle
              if (input.trim()) {
                addTag(input);
              }
            }}
            placeholder={tags.length === 0 ? placeholder : ''}
            size="sm"
          />
        )}
      </div>
      
      {tags.length === maxTags && (
        <small className="text-muted">
          Maksimum etiket sayısına ulaşıldı ({maxTags})
        </small>
      )}
    </div>
  );
};