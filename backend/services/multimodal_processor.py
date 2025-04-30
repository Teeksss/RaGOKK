# Last reviewed: 2025-04-30 06:57:19 UTC (User: Teeksss)
from typing import Dict, Any, List, Optional, Tuple
import os
import base64
import io
import logging
from datetime import datetime
import tempfile
import json
import re
import asyncio

# PIL ve PyMuPDF (görüntü işleme ve PDF analizi için)
from PIL import Image
import fitz  # PyMuPDF

# OpenAI API için gerekli import
from openai import AsyncOpenAI

# Diğer modeller için transformer kütüphanesi
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    from transformers import AutoProcessor, AutoModelForVision2Seq
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

logger = logging.getLogger(__name__)

class MultimodalProcessor:
    """
    Multimodal belge işleme servisi.
    
    Belgelerdeki görseller, tablolar ve grafikleri analiz ederek metin çıkarır.
    """
    
    def __init__(self, 
                use_openai: bool = True,
                model_name: str = "gpt-4-vision-preview",
                local_model_name: str = "Salesforce/blip2-opt-2.7b",
                max_image_size: int = 1024,
                image_format: str = "PNG"):
        """
        Args:
            use_openai: OpenAI modelini kullanmak için
            model_name: OpenAI model adı
            local_model_name: Yerel model adı
            max_image_size: Maksimum görüntü boyutu
            image_format: Görüntü formatı
        """
        self.use_openai = use_openai
        self.model_name = model_name
        self.local_model_name = local_model_name
        self.max_image_size = max_image_size
        self.image_format = image_format
        
        # OpenAI API (gpt-4-vision gibi modeller için)
        if use_openai:
            self.client = AsyncOpenAI()
            
        # Yerel modeller (BLIP-2 veya LLaVA)
        elif HAS_TRANSFORMERS:
            try:
                # BLIP-2 modelini yükle
                self.processor = BlipProcessor.from_pretrained(local_model_name)
                self.model = BlipForConditionalGeneration.from_pretrained(local_model_name)
                logger.info(f"Loaded local VLM model: {local_model_name}")
            except Exception as e:
                logger.error(f"Error loading local VLM model: {str(e)}")
                self.processor = None
                self.model = None
        else:
            logger.warning("Neither OpenAI nor Transformers available for multimodal processing")
    
    async def extract_from_images(self, 
                              images: List[Dict[str, Any]], 
                              query: Optional[str] = None) -> Dict[str, Any]:
        """
        Görüntülerden metin ve içerik çıkarır
        
        Args:
            images: İşlenecek görüntü bilgileri listesi
                   [{"path": "path/to/image.jpg", "page": 1, "box": [0,0,100,100], "type": "figure"}]
            query: Görüntü analizi için isteğe bağlı sorgu
            
        Returns:
            Dict[str, Any]: İşleme sonuçları ve çıkarılan metinler
        """
        if not images:
            return {"success": False, "error": "No images provided"}
            
        try:
            results = []
            
            # Her görüntüyü işle
            for img_info in images:
                img_path = img_info.get("path")
                
                if not img_path or not os.path.exists(img_path):
                    results.append({
                        "image_info": img_info,
                        "success": False, 
                        "error": f"Image not found: {img_path}"
                    })
                    continue
                
                # Görüntü türü
                img_type = img_info.get("type", "figure")
                
                # Görüntüyü işle
                if self.use_openai:
                    caption, extracted_text = await self._process_with_openai(img_path, img_type, query)
                else:
                    caption, extracted_text = await self._process_with_local_model(img_path, img_type, query)
                    
                # Sonucu ekle
                results.append({
                    "image_info": img_info,
                    "success": True,
                    "caption": caption,
                    "extracted_text": extracted_text
                })
            
            return {
                "success": True,
                "results": results,
                "total": len(results),
                "timestamp": datetime.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error extracting from images: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def extract_from_pdf(self, 
                            pdf_path: str, 
                            start_page: int = 0,
                            end_page: Optional[int] = None,
                            query: Optional[str] = None) -> Dict[str, Any]:
        """
        PDF'den görselleri çıkarır ve analiz eder
        
        Args:
            pdf_path: PDF dosya yolu
            start_page: Başlangıç sayfası (0-tabanlı)
            end_page: Bitiş sayfası (dahil)
            query: Görüntü analizi için isteğe bağlı sorgu
            
        Returns:
            Dict[str, Any]: İşleme sonuçları ve çıkarılan metinler
        """
        if not os.path.exists(pdf_path):
            return {"success": False, "error": f"PDF not found: {pdf_path}"}
            
        try:
            # Geçici dizin oluştur
            with tempfile.TemporaryDirectory() as temp_dir:
                # PDF'i aç
                pdf_document = fitz.open(pdf_path)
                
                # Sayfa aralığını sınırla
                page_count = pdf_document.page_count
                start_page = max(0, min(start_page, page_count - 1))
                end_page = min(page_count - 1, end_page) if end_page is not None else page_count - 1
                
                all_images = []
                
                # PDF'den görselleri çıkar
                for page_idx in range(start_page, end_page + 1):
                    page = pdf_document[page_idx]
                    
                    # Görüntüleri çıkar
                    images = await self._extract_images_from_page(page, page_idx, temp_dir)
                    all_images.extend(images)
                    
                    # Tabloları tespit et
                    tables = await self._detect_tables_in_page(page, page_idx, temp_dir)
                    all_images.extend(tables)
                
                # Çıkarılan görselleri işle
                extraction_results = await self.extract_from_images(all_images, query)
                
                # Sonuçları sayfalara göre düzenle
                page_results = {}
                for img_result in extraction_results.get("results", []):
                    img_info = img_result.get("image_info", {})
                    page_num = img_info.get("page")
                    
                    if page_num is not None:
                        if page_num not in page_results:
                            page_results[page_num] = []
                        
                        page_results[page_num].append(img_result)
                
                return {
                    "success": True,
                    "pdf_path": pdf_path,
                    "page_range": {"start": start_page, "end": end_page},
                    "total_images": len(all_images),
                    "page_results": page_results
                }
                
        except Exception as e:
            logger.error(f"Error extracting from PDF: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def process_document_images(self, document_id: str, document_path: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Belge içerisindeki görselleri işler
        
        Args:
            document_id: Belge ID'si
            document_path: Belge dosya yolu
            query: Görüntü analizi için isteğe bağlı sorgu
            
        Returns:
            Dict[str, Any]: İşleme sonuçları
        """
        if not os.path.exists(document_path):
            return {"success": False, "error": f"Document not found: {document_path}"}
        
        try:
            # Dosya uzantısına göre işlem yap
            file_extension = os.path.splitext(document_path)[1].lower()
            
            if file_extension == ".pdf":
                # PDF belgesi
                return await self.extract_from_pdf(document_path, query=query)
            elif file_extension in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp", ".gif"]:
                # Tekli görüntü belgesi
                images = [{
                    "path": document_path,
                    "page": 0,
                    "type": "image"
                }]
                return await self.extract_from_images(images, query=query)
            else:
                # Desteklenmeyen belge türü
                return {"success": False, "error": f"Unsupported document type: {file_extension}"}
                
        except Exception as e:
            logger.error(f"Error processing document images: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _extract_images_from_page(self, page, page_idx: int, output_dir: str) -> List[Dict[str, Any]]:
        """
        PDF sayfasından görselleri çıkarır
        
        Args:
            page: PyMuPDF sayfa nesnesi
            page_idx: Sayfa indeksi
            output_dir: Çıktı dizini
            
        Returns:
            List[Dict[str, Any]]: Çıkarılan görüntü bilgileri
        """
        try:
            images = []
            
            # Sayfadaki görüntü nesnelerini bul
            image_list = page.get_images(full=True)
            
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                
                # Görüntüyü getir
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Görüntüyü kaydet
                img_filename = f"page{page_idx}_img{img_idx}.{self.image_format.lower()}"
                img_path = os.path.join(output_dir, img_filename)
                
                with open(img_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # Görüntü bilgisini ekle
                image_data = {
                    "path": img_path,
                    "page": page_idx,
                    "xref": xref,
                    "type": "image"
                }
                
                # Görüntünün sayfa üzerindeki konumunu bul
                for img_rect in page.get_image_rects(xref):
                    image_data["box"] = [img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1]
                    break
                
                images.append(image_data)
            
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from page: {str(e)}")
            return []
    
    async def _detect_tables_in_page(self, page, page_idx: int, output_dir: str) -> List[Dict[str, Any]]:
        """
        PDF sayfasındaki tabloları tespit eder
        
        Args:
            page: PyMuPDF sayfa nesnesi
            page_idx: Sayfa indeksi
            output_dir: Çıktı dizini
            
        Returns:
            List[Dict[str, Any]]: Tespit edilen tablo görselleri
        """
        try:
            tables = []
            
            # Basit bir tablo tespiti: çizgilerden oluşmuş tablolar
            # Not: Daha gelişmiş tablo tespiti için özelleştirilmiş bir model kullanılabilir
            
            # Sayfadaki çizgileri bul
            lines = page.get_drawings()
            
            # Basit analiz: dikdörtgen şeklindeki alanları bul
            rectangles = []
            for drawing in lines:
                if drawing["type"] == "re":  # Dikdörtgenler
                    rect = drawing["rect"]
                    # Küçük dikdörtgenleri atla (hücre içi çizgiler olabilir)
                    if rect.width > 50 and rect.height > 20:
                        rectangles.append({
                            "x0": rect.x0, 
                            "y0": rect.y0, 
                            "x1": rect.x1, 
                            "y1": rect.y1
                        })
            
            # Tablo olabilecek dikdörtgen alanları işle
            for idx, rect in enumerate(rectangles):
                # Tablonun görüntüsünü oluştur
                table_img_filename = f"page{page_idx}_table{idx}.{self.image_format.lower()}"
                table_img_path = os.path.join(output_dir, table_img_filename)
                
                # Sayfa görüntüsünü oluştur ve ilgili bölümü kes
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x çözünürlük
                pil_img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                
                # Tablo alanını kes
                x0, y0, x1, y1 = rect["x0"]*2, rect["y0"]*2, rect["x1"]*2, rect["y1"]*2  # 2x matrix çarpanı
                table_img = pil_img.crop((x0, y0, x1, y1))
                
                # Kaydet
                table_img.save(table_img_path)
                
                # Tablo bilgisini ekle
                tables.append({
                    "path": table_img_path,
                    "page": page_idx,
                    "box": [rect["x0"], rect["y0"], rect["x1"], rect["y1"]],
                    "type": "table"
                })
            
            return tables
            
        except Exception as e:
            logger.error(f"Error detecting tables in page: {str(e)}")
            return []
    
    async def _process_with_openai(self, 
                                img_path: str, 
                                img_type: str = "figure", 
                                query: Optional[str] = None) -> Tuple[str, str]:
        """
        OpenAI modeli ile görüntüyü işler
        
        Args:
            img_path: Görüntü dosya yolu
            img_type: Görüntü türü (figure, table, chart, diagram, vb.)
            query: İsteğe bağlı sorgu
            
        Returns:
            Tuple[str, str]: Başlık ve çıkarılan metin
        """
        try:
            # Görüntüyü oku ve base64'e çevir
            with open(img_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
                
            # Sorguyu yapılandır
            if not query:
                if img_type == "table":
                    query = "Extract all text content from this table and format it properly as markdown."
                elif img_type == "chart":
                    query = "Describe what this chart shows, including key data points and trends."
                else:  # figure or other
                    query = "Describe this image and extract any text visible in it."
                    
            # Sistem mesajı
            system_message = """
            You are a vision-language assistant that specializes in extracting information from images, particularly from documents.
            For each image, provide two outputs:
            1. A brief caption describing what the image shows
            2. A detailed extraction of all text and information content in the image
            
            For tables, extract the full table content and format it properly as markdown.
            For charts, describe the trends, data points, and labels.
            For diagrams, describe the components and their relationships.
            For regular images, describe the scene and extract any visible text.
            """
            
            # OpenAI API çağrısı
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": [
                        {"type": "text", "text": f"{query}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                    ]}
                ],
                max_tokens=500
            )
            
            # Yanıtı analiz et
            if response.choices and len(response.choices) > 0:
                output = response.choices[0].message.content.strip()
                
                # Başlık ve detaylı metin ayırma
                # Genellikle model çıktıyı "Caption: ... Extracted Text: ..." olarak düzenler
                caption_match = re.search(r"(Caption:|Description:)\s*(.*?)(\n|$)", output, re.IGNORECASE)
                caption = caption_match.group(2).strip() if caption_match else ""
                
                # Başlık çıkarıldıktan sonra kalan metin
                extracted_text = output
                if caption:
                    # Başlıktan sonraki metni al
                    extracted_text = re.sub(r".*?(Caption:|Description:)\s*.*?(\n|$)", "", output, 1, re.IGNORECASE)
                    
                    # "Extracted Text:" gibi etiketleri kaldır
                    extracted_text = re.sub(r"^(Extracted Text:|Detailed Content:|Content:)\s*", "", extracted_text, flags=re.IGNORECASE).strip()
                
                return caption, extracted_text
            else:
                return "", ""
                
        except Exception as e:
            logger.error(f"Error processing image with OpenAI: {str(e)}")
            return "", f"Error: {str(e)}"
    
    async def _process_with_local_model(self, 
                                     img_path: str, 
                                     img_type: str = "figure", 
                                     query: Optional[str] = None) -> Tuple[str, str]:
        """
        Yerel model (BLIP-2) ile görüntüyü işler
        
        Args:
            img_path: Görüntü dosya yolu
            img_type: Görüntü türü
            query: İsteğe bağlı sorgu
            
        Returns:
            Tuple[str, str]: Başlık ve çıkarılan metin
        """
        if not HAS_TRANSFORMERS or not self.processor or not self.model:
            return "", "Error: Local VLM model not available"
            
        try:
            # Görüntüyü yükle
            raw_image = Image.open(img_path).convert('RGB')
            
            # Görüntüyü işle
            if not query:
                # Varsayılan sorgu
                if img_type == "table":
                    query = "Extract the content from this table"
                elif img_type == "chart":
                    query = "Describe what this chart shows"
                else:
                    query = "Describe this image and any text in it"
            
            # Asenkron çalıştırma için ProcessPoolExecutor
            loop = asyncio.get_event_loop()
            
            # Image caption için BLIP-2
            inputs = await loop.run_in_executor(
                None,
                lambda: self.processor(raw_image, query, return_tensors="pt")
            )
            
            out = await loop.run_in_executor(
                None,
                lambda: self.model.generate(**inputs, max_new_tokens=100)
            )
            
            caption = await loop.run_in_executor(
                None,
                lambda: self.processor.decode(out[0], skip_special_tokens=True)
            )
            
            # Daha detaylı açıklama için farklı bir prompt
            detail_query = f"Extract all text and information from this {img_type}"
            
            inputs = await loop.run_in_executor(
                None,
                lambda: self.processor(raw_image, detail_query, return_tensors="pt")
            )
            
            out = await loop.run_in_executor(
                None,
                lambda: self.model.generate(**inputs, max_new_tokens=200)
            )
            
            extracted_text = await loop.run_in_executor(
                None,
                lambda: self.processor.decode(out[0], skip_special_tokens=True)
            )
            
            return caption, extracted_text
            
        except Exception as e:
            logger.error(f"Error processing image with local model: {str(e)}")
            return "", f"Error: {str(e)}"