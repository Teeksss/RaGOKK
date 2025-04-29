# Last reviewed: 2025-04-29 11:44:12 UTC (User: Teekssseskikleri tamamla)
import os
from typing import Optional, List, Dict, Any, Union, Tuple
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import logging

# EasyOCR (opsiyonel)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRProcessor:
    """
    OCR işlemleri için sınıf
    Hem Tesseract hem de EasyOCR (varsa) destekler
    """
    
    def __init__(self, engine: str = "tesseract", languages: List[str] = ["eng", "tur"]):
        """
        OCR işlemcisini başlat
        
        Args:
            engine: OCR motoru ('tesseract' veya 'easyocr')
            languages: Desteklenen diller
        """
        self.engine = engine
        self.languages = languages
        
        # Tesseract yolunu kontrol et
        if engine == "tesseract":
            self._setup_tesseract()
        
        # EasyOCR okuyucusu
        self.reader = None
        if engine == "easyocr":
            self._setup_easyocr()
    
    def _setup_tesseract(self):
        """Tesseract yapılandırması"""
        # Windows için Tesseract yolunu ayarla
        if os.name == 'nt':
            tesseract_cmd = os.getenv('TESSERACT_PATH', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
            if os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            else:
                logger.warning(f"Tesseract bulunamadı: {tesseract_cmd}")
                
        # Test et
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            logger.error(f"Tesseract başlatma hatası: {e}")
            logger.warning("Tesseract düzgün yapılandırılmamış. OCR işlemleri başarısız olabilir.")
    
    def _setup_easyocr(self):
        """EasyOCR yapılandırması"""
        if not EASYOCR_AVAILABLE:
            logger.warning("EasyOCR yüklü değil, pip install easyocr komutu ile yükleyin.")
            return
            
        try:
            # EasyOCR okuyucusu oluştur
            # NOT: GPU'yu otomatik algılar
            self.reader = easyocr.Reader(
                lang_list=self.languages,
                gpu=True,  # GPU varsa kullan
                model_storage_directory=os.getenv('EASYOCR_MODEL_PATH', None),
                download_enabled=True
            )
            logger.info(f"EasyOCR başlatıldı, diller: {', '.join(self.languages)}")
            
        except Exception as e:
            logger.error(f"EasyOCR başlatma hatası: {e}")
            logger.warning("EasyOCR başlatılamadı, Tesseract'a geri dönülecek.")
            self.engine = "tesseract"
    
    def process_image(self, image: Union[str, np.ndarray, Image.Image, bytes]) -> str:
        """
        Resimden metin çıkarmak için OCR uygular
        
        Args:
            image: Resim dosyası yolu, numpy array, PIL Image veya bytes
            
        Returns:
            str: Çıkarılan metin
        """
        # Resmi normalize et
        img = self._normalize_image_input(image)
        
        if img is None:
            logger.error("Resim okunamadı veya işlenemedi")
            return ""
        
        # OCR motoruna göre işlem yap
        if self.engine == "easyocr" and EASYOCR_AVAILABLE and self.reader:
            return self._process_with_easyocr(img)
        else:
            # Varsayılan olarak Tesseract kullan
            return self._process_with_tesseract(img)
    
    def _normalize_image_input(self, image: Union[str, np.ndarray, Image.Image, bytes]) -> Optional[np.ndarray]:
        """
        Farklı türlerdeki girişleri OpenCV numpy array'e çevirir
        
        Args:
            image: Resim dosyası yolu, numpy array, PIL Image veya bytes
            
        Returns:
            Optional[np.ndarray]: OpenCV formatında resim
        """
        try:
            if isinstance(image, str):
                # Dosya yolu
                return cv2.imread(image)
                
            elif isinstance(image, np.ndarray):
                # Zaten numpy array
                return image
                
            elif isinstance(image, Image.Image):
                # PIL Image
                return np.array(image.convert('RGB'))
                
            elif isinstance(image, bytes):
                # Bytes (örn. PDF'den çıkarılan resim)
                nparr = np.frombuffer(image, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
            else:
                logger.error(f"Desteklenmeyen resim türü: {type(image)}")
                return None
                
        except Exception as e:
            logger.error(f"Resim normalleştirme hatası: {e}")
            return None
    
    def _process_with_tesseract(self, image: np.ndarray) -> str:
        """Tesseract ile OCR işlemi"""
        try:
            # Ön işleme
            img = self._preprocess_image(image)
            
            # Dil seçimi
            lang = '+'.join(self.languages)
            
            # OCR uygula
            text = pytesseract.image_to_string(img, lang=lang)
            
            return text
            
        except Exception as e:
            logger.error(f"Tesseract OCR hatası: {e}")
            return ""
    
    def _process_with_easyocr(self, image: np.ndarray) -> str:
        """EasyOCR ile OCR işlemi"""
        try:
            # Ön işleme (EasyOCR kendi ön işlemesini yapıyor, ama kaliteyi artırmak için)
            img = self._preprocess_image(image, for_easyocr=True)
            
            # OCR uygula
            results = self.reader.readtext(img)
            
            # Sonuçları birleştir
            texts = []
            for (_, text, _) in results:
                texts.append(text)
            
            return '\n'.join(texts)
            
        except Exception as e:
            logger.error(f"EasyOCR hatası: {e}")
            # Tesseract'a geri dön
            return self._process_with_tesseract(image)
    
    def _preprocess_image(self, image: np.ndarray, for_easyocr: bool = False) -> np.ndarray:
        """
        OCR için resmi ön işler
        
        Args:
            image: OpenCV formatında resim
            for_easyocr: EasyOCR için optimize edilmiş işleme
            
        Returns:
            np.ndarray: İşlenmiş resim
        """
        # Gri tonlama
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # EasyOCR için farklı bir işleme kullan (daha az agresif)
        if for_easyocr:
            # Hafif dengeleme
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            return gray
            
        # Tesseract için daha agresif işleme
        # Gürültü azaltma
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Otomatik eşikleme (thresholding)
        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Dilasyon ve erozyon
        kernel = np.ones((1, 1), np.uint8)
        img = cv2.dilate(thresh, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)
        
        return img