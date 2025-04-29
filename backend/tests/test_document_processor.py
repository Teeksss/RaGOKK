# Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
import json

from ..services.document_processor import DocumentProcessor

# PDF içeriği için Mock
MOCK_PDF_CONTENT = b'%PDF-1.5\nTest PDF Content'
# DOCX içeriği için Mock
MOCK_DOCX_CONTENT = b'PK\x03\x04\x14\x00\x06\x00Test DOCX Content'
# TXT içeriği için Mock
MOCK_TXT_CONTENT = "Bu bir test metnidir.\nTürkçe karakterler içerir: çğıöşü"

@pytest.fixture
def document_processor():
    return DocumentProcessor()

@patch('backend.services.document_processor.PyPDF2.PdfReader')
async def test_process_pdf(mock_pdf_reader, document_processor):
    # Mock PDF okuyucu
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [MagicMock(), MagicMock()]
    mock_reader_instance.pages[0].extract_text.return_value = "Test Page 1"
    mock_reader_instance.pages[1].extract_text.return_value = "Test Page 2"
    mock_reader_instance.metadata = {'/Title': 'Test PDF', '/Author': 'Test Author'}
    
    mock_pdf_reader.return_value = mock_reader_instance
    
    # tempfile.NamedTemporaryFile için mock
    with patch('backend.services.document_processor.tempfile.NamedTemporaryFile', 
              mock_open(read_data=MOCK_PDF_CONTENT)) as mock_file:
        mock_file.return_value.__enter__.return_value.name = '/tmp/test.pdf'
        
        # PDF işleme
        result = await document_processor._process_pdf(MOCK_PDF_CONTENT)
        
        # Sonuçları kontrol et
        assert isinstance(result, tuple)
        text, metadata = result
        
        # Metin içeriği doğru mu?
        assert "Test Page 1" in text
        assert "Test Page 2" in text
        
        # Metadata doğru mu?
        assert metadata['pages'] == 2
        assert metadata['Title'] == 'Test PDF'
        assert metadata['Author'] == 'Test Author'

@patch('backend.services.document_processor.docx.Document')
async def test_process_docx(mock_docx, document_processor):
    # Mock DOCX dokümanı
    mock_doc = MagicMock()
    mock_doc.paragraphs = [MagicMock(), MagicMock()]
    mock_doc.paragraphs[0].text = "Test Paragraph 1"
    mock_doc.paragraphs[1].text = "Test Paragraph 2"
    
    mock_table = MagicMock()
    mock_row = MagicMock()
    mock_cell1 = MagicMock()
    mock_cell1.text = "Cell 1"
    mock_cell2 = MagicMock()
    mock_cell2.text = "Cell 2"
    mock_row.cells = [mock_cell1, mock_cell2]
    mock_table.rows = [mock_row]
    
    mock_doc.tables = [mock_table]
    
    mock_core_props = MagicMock()
    mock_core_props.title = "Test Document"
    mock_core_props.author = "Test Author"
    mock_core_props.created = "2023-01-01"
    
    mock_doc.core_properties = mock_core_props
    
    mock_docx.return_value = mock_doc
    
    # tempfile.NamedTemporaryFile için mock
    with patch('backend.services.document_processor.tempfile.NamedTemporaryFile', 
              mock_open(read_data=MOCK_DOCX_CONTENT)) as mock_file:
        mock_file.return_value.__enter__.return_value.name = '/tmp/test.docx'
        
        # DOCX işleme
        result = await document_processor._process_docx(MOCK_DOCX_CONTENT)
        
        # Sonuçları kontrol et
        assert isinstance(result, tuple)
        text, metadata = result
        
        # Metin içeriği doğru mu?
        assert "Test Paragraph 1" in text
        assert "Test Paragraph 2" in text
        assert "Cell 1 | Cell 2" in text
        
        # Metadata doğru mu?
        assert metadata['paragraphs'] == 2
        assert metadata['tables'] == 1
        assert metadata['title'] == "Test Document"
        assert metadata['author'] == "Test Author"

async def test_process_txt(document_processor):
    # TXT işleme
    result = await document_processor._process_txt(MOCK_TXT_CONTENT)
    
    # Sonuçları kontrol et
    assert isinstance(result, tuple)
    text, metadata = result
    
    # Metin içeriği doğru mu?
    assert "Bu bir test metnidir." in text
    assert "Türkçe karakterler içerir: çğıöşü" in text
    
    # Metadata doğru mu?
    assert metadata['encoding'] == 'utf-8'
    assert metadata['line_count'] == 2

@patch('backend.services.document_processor.langdetect.detect')
async def test_detect_language(mock_detect, document_processor):
    # Türkçe metin
    mock_detect.return_value = 'tr'
    text = "Bu bir Türkçe metindir ve Türkçe karakterler içerir: çğıöşüÇĞİÖŞÜ"
    language = document_processor._detect_language(text)
    assert language == 'tr'
    
    # İngilizce metin
    mock_detect.return_value = 'en'
    text = "This is an English text with English characters."
    language = document_processor._detect_language(text)
    assert language == 'en'
    
    # Boş metin
    language = document_processor._detect_language("")
    assert language == 'unknown'

@patch('backend.services.document_processor.Translator')
async def test_translate_text(mock_translator, document_processor):
    # Mock çevirmen
    mock_translator_instance = MagicMock()
    mock_translation = MagicMock()
    mock_translation.text = "This is a test text. It contains Turkish characters."
    mock_translator_instance.translate.return_value = mock_translation
    
    mock_translator.return_value = mock_translator_instance
    document_processor.translator = mock_translator_instance
    
    # Çeviri testi
    text = "Bu bir test metnidir. Türkçe karakterler içerir: çğıöşü"
    translated = await document_processor.translate_text(text, 'en')
    
    # Çevirmen çağrıldı mı?
    mock_translator_instance.translate.assert_called_once()
    
    # Çeviri doğru mu?
    assert translated == "This is a test text. It contains Turkish characters."