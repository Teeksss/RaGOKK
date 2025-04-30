// Last reviewed: 2025-04-30 12:03:45 UTC (User: TeeksssBelgeleri)
import React, { useState, useEffect } from 'react';
import { Form, Button, Badge } from 'react-bootstrap';
import { FaFile, FaFilePdf, FaFileWord, FaFileExcel, FaFilePowerpoint, FaFileAlt, FaFileImage, FaFileCode } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import { DocumentType } from '../../types/document.types';

interface DocumentTypeFilterProps {
  selectedTypes: DocumentType[];
  availableTypes: DocumentType[];
  onChange: (types: DocumentType[]) => void;
  typeCounts?: Record<DocumentType, number>;
  maxVisible?: number;
  showSelectAll?: boolean;
}

const DocumentTypeFilter: React.FC<DocumentTypeFilterProps> = ({
  selectedTypes,
  availableTypes,
  onChange,
  typeCounts = {},
  maxVisible = 6,
  showSelectAll = true,
}) => {
  const { t } = useTranslation();
  const [showAll, setShowAll] = useState(false);
  const [visibleTypes, setVisibleTypes] = useState<DocumentType[]>([]);
  
  // Dosya türlerini popülerlik ve sayılarına göre sırala
  useEffect(() => {
    const sortedTypes = [...availableTypes].sort((a, b) => {
      // Önce seçili olanları göster
      if (selectedTypes.includes(a) && !selectedTypes.includes(b)) return -1;
      if (!selectedTypes.includes(a) && selectedTypes.includes(b)) return 1;
      
      // Sonra sayılarına göre sırala
      const countA = typeCounts[a] || 0;
      const countB = typeCounts[b] || 0;
      return countB - countA;
    });
    
    setVisibleTypes(sortedTypes);
  }, [availableTypes, selectedTypes, typeCounts]);
  
  // Dosya türüne göre ikon seçimi
  const getIconForType = (type: DocumentType) => {
    switch (type) {
      case 'pdf':
        return <FaFilePdf className="text-danger" />;
      case 'doc':
      case 'docx':
        return <FaFileWord className="text-primary" />;
      case 'xls':
      case 'xlsx':
        return <FaFileExcel className="text-success" />;
      case 'ppt':
      case 'pptx':
        return <FaFilePowerpoint className="text-warning" />;
      case 'txt':
      case 'rtf':
      case 'md':
        return <FaFileAlt className="text-secondary" />;
      case 'image':
        return <FaFileImage className="text-info" />;
      case 'json':
      case 'xml':
      case 'html':
        return <FaFileCode className="text-dark" />;
      default:
        return <FaFile className="text-muted" />;
    }
  };
  
  // Dosya türü değişikliği
  const handleTypeChange = (type: DocumentType, checked: boolean) => {
    if (checked) {
      onChange([...selectedTypes, type]);
    } else {
      onChange(selectedTypes.filter(t => t !== type));
    }
  };
  
  // Tümünü seç/kaldır
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onChange([...availableTypes]);
    } else {
      onChange([]);
    }
  };
  
  // Görünür türleri belirle
  const displayedTypes = showAll ? visibleTypes : visibleTypes.slice(0, maxVisible);
  
  return (
    <div className="document-type-filter mb-3">
      <h6 className="filter-title">{t('documents.filters.fileTypes')}</h6>
      
      {showSelectAll && (
        <Form.Check
          id="select-all-types"
          type="checkbox"
          label={t('common.selectAll')}
          checked={selectedTypes.length === availableTypes.length}
          onChange={(e) => handleSelectAll(e.target.checked)}
          className="mb-2"
        />
      )}
      
      <div className="document-type-list">
        {displayedTypes.map((type) => (
          <div key={type} className="document-type-item">
            <Form.Check
              id={`type-${type}`}
              type="checkbox"
              checked={selectedTypes.includes(type)}
              onChange={(e) => handleTypeChange(type, e.target.checked)}
              label={
                <span className="d-flex align-items-center">
                  {getIconForType(type)}
                  <span className="ms-2">{t(`documents.types.${type}`)}</span>
                  {typeCounts && typeCounts[type] > 0 && (
                    <Badge bg="secondary" pill className="ms-2">
                      {typeCounts[type]}
                    </Badge>
                  )}
                </span>
              }
            />
          </div>
        ))}
      </div>
      
      {availableTypes.length > maxVisible && (
        <Button
          variant="link"
          size="sm"
          onClick={() => setShowAll(!showAll)}
          className="p-0 mt-1"
        >
          {showAll
            ? t('common.showLess')
            : t('common.showMore', { count: availableTypes.length - maxVisible })}
        </Button>
      )}
    </div>
  );
};

export default React.memo(DocumentTypeFilter);