# Last reviewed: 2025-04-29 11:15:42 UTC (User: TeeksssPDF)
import os
import tempfile
from typing import Dict, List, Optional, Any, BinaryIO, Union, Tuple
import datetime
import uuid

# Format Handlers
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import docx
import PyPDF2
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, inspect

# OCR ve Dil İşleme
import pytesseract
import cv2
import numpy as np
from PIL import Image
import langdetect
from googletrans import Translator

from ..utils.logger import get_logger

logger = get_logger(__name__)

class DocumentProcessor:
    """
    Farklı formatlardaki dokümanları işleyen ve vektör depo için hazırlayan sınıf.
    Desteklenen formatlar: PDF, DOCX, TXT, HTML, XML, JSON, CSV, veritabanı sorguları
    """
    
    def __init__(self):
        # Format işleyiciler
        self.format_handlers = {
            'pdf': self._process_pdf,
            'docx': self._process_docx,
            'txt': self._process_txt,
            'html': self._process_html,
            'xml': self._process_xml,
            'json': self._process_json,
            'csv': self._process_csv,
            'sql': self._process_sql_query
        }
        
        # Görüntü işleme için OCR ayarları
        try:
            # Tesseract yolunu ayarla (Windows'ta gerekli)
            if os.name == 'nt':  # Windows
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        except Exception as e:
            logger.warning(f"Tesseract yapılandırması yüklenemedi: {e}")
            
        # Çevirmen nesnesi
        self.translator = None
        try:
            self.translator = Translator()
        except Exception as e:
            logger.warning(f"Google Translate API başlatılamadı: {e}")
    
    async def process_document(self, 
                             file_content: Union[bytes, BinaryIO, str],
                             file_format: str,
                             file_name: Optional[str] = None,
                             metadata: Optional[Dict] = None
                            ) -> Dict[str, Any]:
        """
        Dokümanı işler ve metin içeriği, meta veriler ile birlikte döndürür.
        
        Args:
            file_content: Dosya içeriği (bytes, file-like nesne veya string olabilir)
            file_format: Dosya formatı (pdf, docx, txt, vb.)
            file_name: Dosya adı (opsiyonel)
            metadata: Ek meta veriler (opsiyonel)
            
        Returns:
            Dict: Doküman içeriği ve meta verileri
        """
        start_time = datetime.datetime.now()
        
        # Varsayılan meta verileri ayarla
        doc_metadata = {
            "source_type": file_format,
            "processing_date": datetime.datetime.utcnow().isoformat(),
            "file_name": file_name,
            "doc_id": str(uuid.uuid4())
        }
        
        # Ek meta verileri ekle
        if metadata:
            doc_metadata.update(metadata)
        
        try:
            # Format için uygun işleyiciyi bul
            handler = self.format_handlers.get(file_format.lower())
            
            if not handler:
                raise ValueError(f"Desteklenmeyen dosya formatı: {file_format}")
            
            # Dokümanı işle
            text_content, extracted_metadata = await handler(file_content)
            
            # İşlenen içeriği kontrol et
            if not text_content:
                logger.warning(f"Dosyadan metin çıkarılamadı: {file_name}")
                text_content = ""
            
            # Çıkarılan meta verileri ekle
            doc_metadata.update(extracted_metadata)
            
            # Dil tespiti yap
            language = self._detect_language(text_content)
            doc_metadata["language"] = language
            
            # İşleme süresini hesapla
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            doc_metadata["processing_time"] = processing_time
            
            # Doküman uzunluğunu kaydet
            doc_metadata["char_count"] = len(text_content)
            doc_metadata["word_count"] = len(text_content.split())
            
            return {
                "content": text_content,
                "metadata": doc_metadata
            }
            
        except Exception as e:
            logger.error(f"Doküman işleme hatası ({file_format}): {str(e)}")
            
            # Hata bilgisini meta verilere ekle
            doc_metadata["error"] = str(e)
            doc_metadata["processing_status"] = "failed"
            
            return {
                "content": "",
                "metadata": doc_metadata
            }
    
    async def _process_pdf(self, file_content: Union[bytes, BinaryIO]) -> Tuple[str, Dict[str, Any]]:
        """PDF dosyasını işler"""
        extracted_text = ""
        metadata = {"pages": 0, "has_ocr": False}
        
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Dosya içeriği bytes mi yoksa file-like nesne mi?
            if isinstance(file_content, bytes):
                temp_file.write(file_content)
            else:
                # file-like nesne ise, içeriğini oku ve yaz
                temp_file.write(file_content.read())
            
            temp_file_path = temp_file.name
        
        try:
            # PDF'i aç
            with open(temp_file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                metadata["pages"] = len(pdf_reader.pages)
                
                # Sayfa içeriklerini topla
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    # Metin çıkarılamadıysa, OCR dene
                    if not page_text or len(page_text.strip()) < 100:  # Sayfa çok az metin içeriyorsa
                        # PDF sayfasını resime dönüştür ve OCR uygula
                        try:
                            page_image = self._pdf_page_to_image(temp_file_path, page_num)
                            if page_image is not None:
                                page_text = self._apply_ocr(page_image)
                                metadata["has_ocr"] = True
                        except Exception as e:
                            logger.warning(f"OCR işlemi sırasında hata: {e}")
                    
                    # Sayfayı sonuca ekle
                    if page_text:
                        extracted_text += page_text + "\n\n"
                        
                # PDF meta verilerini çıkar
                if pdf_reader.metadata:
                    for key, value in pdf_reader.metadata.items():
                        if value:
                            clean_key = key[1:] if key.startswith('/') else key
                            metadata[clean_key] = str(value)
        
        finally:
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
                
        return extracted_text, metadata
    
    def _pdf_page_to_image(self, pdf_path: str, page_num: int) -> Optional[np.ndarray]:
        """PDF sayfasını resime dönüştürür (OCR için)"""
        try:
            import fitz  # PyMuPDF
            
            # PDF'i aç
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            
            # Sayfayı resim olarak render et
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # PIL Image'i numpy array'e dönüştür
            return np.array(img)
        except ImportError:
            logger.warning("PyMuPDF (fitz) kütüphanesi bulunamadı. OCR için PDF sayfası resme dönüştürülemedi.")
            return None
        except Exception as e:
            logger.error(f"PDF sayfası resme dönüştürülürken hata: {e}")
            return None
    
    async def _process_docx(self, file_content: Union[bytes, BinaryIO]) -> Tuple[str, Dict[str, Any]]:
        """DOCX dosyasını işler"""
        extracted_text = ""
        metadata = {}
        
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
            # Dosya içeriği bytes mi yoksa file-like nesne mi?
            if isinstance(file_content, bytes):
                temp_file.write(file_content)
            else:
                # file-like nesne ise, içeriğini oku ve yaz
                temp_file.write(file_content.read())
            
            temp_file_path = temp_file.name
        
        try:
            # DOCX'i aç
            doc = docx.Document(temp_file_path)
            
            # Paragrafları oku
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            # Tabloları oku
            for table in doc.tables:
                for row in table.rows:
                    row_text = ' | '.join(cell.text for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            
            # Tüm metni birleştir
            extracted_text = '\n\n'.join(paragraphs)
            
            # Meta verileri çıkar
            metadata["paragraphs"] = len(doc.paragraphs)
            metadata["tables"] = len(doc.tables)
            
            # Core özelliklerini çıkarmaya çalış
            try:
                core_props = doc.core_properties
                metadata["title"] = core_props.title
                metadata["author"] = core_props.author
                metadata["created"] = str(core_props.created) if core_props.created else None
                metadata["modified"] = str(core_props.modified) if core_props.modified else None
            except:
                logger.debug("DOCX core özellikleri çıkarılamadı")
                
        finally:
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
                
        return extracted_text, metadata
    
    async def _process_txt(self, file_content: Union[bytes, str]) -> Tuple[str, Dict[str, Any]]:
        """Düz metin dosyasını işler"""
        # Dosya içeriğini string'e çevir
        if isinstance(file_content, bytes):
            # Farklı kodlamaları dene
            encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-9']
            text = None
            
            for encoding in encodings:
                try:
                    text = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if text is None:
                # Hiçbir kodlama başarılı olmadıysa, hatalar yok sayılarak UTF-8 kullan
                text = file_content.decode('utf-8', errors='ignore')
        else:
            # Zaten string ise
            text = file_content
        
        # Meta veri
        metadata = {
            "encoding": "utf-8",
            "line_count": text.count('\n') + 1
        }
        
        return text, metadata
    
    async def _process_html(self, file_content: Union[bytes, str]) -> Tuple[str, Dict[str, Any]]:
        """HTML dosyasını işler"""
        # HTML içeriğini string'e çevir
        if isinstance(file_content, bytes):
            html_content = file_content.decode('utf-8', errors='ignore')
        else:
            html_content = file_content
        
        # BeautifulSoup ile parse et
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Meta verileri çıkar
        metadata = {
            "title": soup.title.string if soup.title else None,
            "has_tables": len(soup.find_all('table')) > 0,
            "images": len(soup.find_all('img')),
            "links": len(soup.find_all('a')),
            "headings": len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        }
        
        # Metni çıkar (script ve style etiketlerini kaldır)
        for script in soup(["script", "style"]):
            script.extract()
        
        # Düz metni al
        text = soup.get_text(separator='\n')
        
        # Fazladan boşlukları temizle
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text, metadata
    
    async def _process_xml(self, file_content: Union[bytes, str]) -> Tuple[str, Dict[str, Any]]:
        """XML dosyasını işler"""
        # XML içeriğini string'e çevir
        if isinstance(file_content, bytes):
            xml_content = file_content.decode('utf-8', errors='ignore')
        else:
            xml_content = file_content
        
        # XML'i parse et
        try:
            root = ET.fromstring(xml_content)
            
            # Düz metin içeriği çıkar
            def extract_text_from_element(element):
                text = element.text or ""
                for child in element:
                    text += extract_text_from_element(child)
                    if child.tail:
                        text += child.tail
                return text
            
            extracted_text = extract_text_from_element(root)
            
            # Meta verileri çıkar
            metadata = {
                "root_tag": root.tag,
                "elements_count": len(root.findall(".//*")),
                "attributes_count": sum(len(elem.attrib) for elem in root.findall(".//*"))
            }
            
            return extracted_text, metadata
            
        except Exception as e:
            logger.error(f"XML işleme hatası: {e}")
            return "", {"error": str(e)}
    
    async def _process_json(self, file_content: Union[bytes, str]) -> Tuple[str, Dict[str, Any]]:
        """JSON dosyasını işler"""
        # JSON içeriğini string'e çevir
        if isinstance(file_content, bytes):
            json_content = file_content.decode('utf-8', errors='ignore')
        else:
            json_content = file_content
        
        try:
            # JSON'ı parse et
            data = json.loads(json_content)
            
            # JSON'ı metne dönüştür (düz metin temsili)
            def json_to_text(obj, level=0):
                indent = "  " * level
                result = []
                
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            result.append(f"{indent}{key}:")
                            result.append(json_to_text(value, level + 1))
                        else:
                            result.append(f"{indent}{key}: {value}")
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            result.append(f"{indent}Item {i+1}:")
                            result.append(json_to_text(item, level + 1))
                        else:
                            result.append(f"{indent}Item {i+1}: {item}")
                else:
                    result.append(f"{indent}{obj}")
                
                return "\n".join(result)
            
            extracted_text = json_to_text(data)
            
            # Meta verileri çıkar
            def count_items(obj):
                if isinstance(obj, dict):
                    return len(obj) + sum(count_items(v) for v in obj.values() if isinstance(v, (dict, list)))
                elif isinstance(obj, list):
                    return len(obj) + sum(count_items(item) for item in obj if isinstance(item, (dict, list)))
                else:
                    return 0
            
            metadata = {
                "structure": "object" if isinstance(data, dict) else "array",
                "top_level_items": len(data) if isinstance(data, (dict, list)) else 1,
                "total_nested_items": count_items(data)
            }
            
            return extracted_text, metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}")
            return "", {"error": f"JSON parse hatası: {str(e)}"}
        except Exception as e:
            logger.error(f"JSON işleme hatası: {e}")
            return "", {"error": str(e)}
    
    async def _process_csv(self, file_content: Union[bytes, BinaryIO]) -> Tuple[str, Dict[str, Any]]:
        """CSV dosyasını işler"""
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            if isinstance(file_content, bytes):
                temp_file.write(file_content)
            else:
                temp_file.write(file_content.read())
            
            temp_file_path = temp_file.name
        
        try:
            # CSV'yi pandas DataFrame'e yükle
            df = pd.read_csv(temp_file_path)
            
            # DataFrame'i metne dönüştür
            text_content = df.to_string(index=False)
            
            # Meta verileri çıkar
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist()
            }
            
            return text_content, metadata
            
        except Exception as e:
            logger.error(f"CSV işleme hatası: {e}")
            return "", {"error": str(e)}
        finally:
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    
    async def _process_sql_query(self, query_content: str) -> Tuple[str, Dict[str, Any]]:
        """SQL sorgu sonucunu işler"""
        # SQL sorgusunu ve bağlantı bilgilerini parse et
        try:
            # query_content formatı: "connection_string||SQL_QUERY"
            parts = query_content.split("||", 1)
            
            if len(parts) != 2:
                return "", {"error": "Geçersiz sorgu formatı. 'connection_string||SQL_QUERY' formatı kullanılmalıdır"}
            
            connection_string = parts[0]
            sql_query = parts[1]
            
            # Veritabanına bağlan
            engine = create_engine(connection_string)
            
            # Sorguyu çalıştır
            with engine.connect() as connection:
                result = pd.read_sql(sql_query, connection)
            
            # Sonuçları metne dönüştür
            text_content = result.to_string(index=False)
            
            # Meta verileri çıkar
            metadata = {
                "rows": len(result),
                "columns": len(result.columns),
                "column_names": result.columns.tolist(),
                "db_type": engine.name
            }
            
            return text_content, metadata
            
        except Exception as e:
            logger.error(f"SQL sorgu işleme hatası: {e}")
            return "", {"error": f"SQL sorgu hatası: {str(e)}"}
    
    def _apply_ocr(self, image: Union[str, np.ndarray]) -> str:
        """Resime OCR uygulayarak metin çıkarır"""
        try:
            # Resim dosya yolu ise, oku
            if isinstance(image, str):
                img = cv2.imread(image)
            else:
                img = image
            
            # Görüntüyü ön işleme
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # OCR uygula
            text = pytesseract.image_to_string(thresh, lang='eng+tur')
            
            return text
        except Exception as e:
            logger.error(f"OCR işleme hatası: {e}")
            return ""
    
    def _detect_language(self, text: str) -> str:
        """Metin dilini tespit eder"""
        # Kısa metinler için dil algılama sorunlu olabilir
        if not text or len(text.strip()) < 50:
            return "unknown"
            
        try:
            # Dil algılama
            lang = langdetect.detect(text[:1000])  # İlk 1000 karakteri kullan
            return lang
        except Exception as e:
            logger.debug(f"Dil algılama hatası: {e}")
            return "unknown"
    
    async def translate_text(self, text: str, target_language: str = 'en') -> str:
        """Metni hedef dile çevirir"""
        if not self.translator:
            try:
                self.translator = Translator()
            except Exception as e:
                logger.error(f"Google Translate API başlatılamadı: {e}")
                return text
                
        # Boş veya çok kısa metin kontrolü
        if not text or len(text.strip()) < 5:
            return text
            
        try:
            # Dil algılama
            source_lang = self._detect_language(text)
            
            # Zaten hedef dilde ise, çevirme
            if source_lang == target_language:
                return text
                
            # Metni çevir
            # Uzun metinleri parçalara böl (Google Translate API sınırı ~5000 karakter)
            max_chunk_size = 4000
            chunks = []
            
            # Metni paragraflarla böl
            paragraphs = text.split('\n')
            current_chunk = ""
            
            for paragraph in paragraphs:
                # Eğer paragraf eklendiğinde chunk limiti aşılırsa, yeni chunk başlat
                if len(current_chunk) + len(paragraph) + 1 > max_chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    if current_chunk:
                        current_chunk += '\n'
                    current_chunk += paragraph
            
            # Son chunk'ı ekle
            if current_chunk:
                chunks.append(current_chunk)
                
            # Her chunk'ı çevir
            translated_chunks = []
            for chunk in chunks:
                translation = self.translator.translate(chunk, src=source_lang, dest=target_language)
                translated_chunks.append(translation.text)
            
            # Çevirileri birleştir
            return '\n'.join(translated_chunks)
            
        except Exception as e:
            logger.error(f"Çeviri hatası: {e}")
            return text