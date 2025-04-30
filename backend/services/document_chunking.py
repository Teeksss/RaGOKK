# Last reviewed: 2025-04-29 14:43:27 UTC (User: Teeksss)
import logging
from typing import List, Dict, Any, Optional, Union
import re
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter, 
    MarkdownTextSplitter, 
    HTMLTextSplitter,
    PythonCodeTextSplitter,
    JavascriptTextSplitter
)

logger = logging.getLogger(__name__)

class DocumentChunker:
    """
    Gelişmiş belge bölümleme sistemi
    
    Bu sınıf, farklı belge türleri için optimize edilmiş bölümleme stratejileri sağlar:
    - Genel metin
    - Markdown
    - HTML
    - Kaynak kodu (Python, JavaScript, vb.)
    - PDF tabanlı belgeler (özel mantıksal bölümleme)
    - Tablo ve yapılandırılmış veri (CSV, JSON)
    """
    
    def __init__(self):
        """DocumentChunker başlat"""
        # Varsayılan ayarlar
        self.default_chunk_size = 1000
        self.default_chunk_overlap = 200
        
        # Bölümleme türleri
        self.text_types = {
            "plain": self._create_text_splitter,
            "markdown": self._create_markdown_splitter,
            "html": self._create_html_splitter,
            "python": self._create_python_splitter,
            "javascript": self._create_javascript_splitter,
            "typescript": self._create_javascript_splitter,
            "java": self._create_code_splitter,
            "c": self._create_code_splitter,
            "cpp": self._create_code_splitter,
            "csharp": self._create_code_splitter,
            "go": self._create_code_splitter,
            "rust": self._create_code_splitter,
            "swift": self._create_code_splitter,
            "php": self._create_code_splitter,
            "ruby": self._create_code_splitter,
            "pdf": self._create_pdf_splitter,
            "csv": self._create_csv_splitter,
            "json": self._create_json_splitter,
            "xml": self._create_xml_splitter
        }
    
    def _create_text_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        Genel metin bölücü oluştur
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _create_markdown_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        Markdown formatı için bölücü oluştur
        """
        return MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def _create_html_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        HTML formatı için bölücü oluştur
        """
        return HTMLTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def _create_python_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        Python kodu için bölücü oluştur
        """
        return PythonCodeTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def _create_javascript_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        JavaScript/TypeScript kodu için bölücü oluştur
        """
        return JavascriptTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def _create_code_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        Genel kod bölücü oluştur
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "}", "{", ";", " ", ""]
        )
    
    def _create_pdf_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        PDF metin bölücü oluştur (özel formatlanmış)
        """
        # PDF için özel ayraçlar ekleyerek sayfa ve bölüm bölünmelerine duyarlı
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".\n", ". ", " ", ""]
        )
    
    def _create_csv_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        CSV bölücü oluştur
        """
        # CSV satırlarını mantıksal gruplar halinde böl
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,  # CSV için örtüşme kullanma
            length_function=len,
            separators=["\n\n", "\n", ""]
        )
    
    def _create_json_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        JSON bölücü oluştur
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["},\n", "}\n", "},", "}", "{", ",", " ", ""]
        )
    
    def _create_xml_splitter(self, chunk_size: int, chunk_overlap: int):
        """
        XML bölücü oluştur
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["</", ">", "<", " ", ""]
        )
    
    def get_document_type(self, content: str, file_extension: str = '') -> str:
        """
        İçerik türünü anlamaya çalış
        
        Args:
            content: Belge içeriği
            file_extension: Dosya uzantısı (opsiyonel ipucu)
            
        Returns:
            str: Belge türü ('plain', 'markdown', 'html', vb.)
        """
        # Dosya uzantısı varsa kullan
        if file_extension:
            ext = file_extension.lower().lstrip('.')
            
            # Yaygın markdown uzantıları
            if ext in ['md', 'markdown', 'mdown', 'mkd']:
                return 'markdown'
                
            # HTML uzantıları
            elif ext in ['html', 'htm', 'xhtml']:
                return 'html'
                
            # Kod uzantıları
            elif ext in ['py']:
                return 'python'
            elif ext in ['js']:
                return 'javascript'
            elif ext in ['ts']:
                return 'typescript'
            elif ext in ['java']:
                return 'java'
            elif ext in ['c', 'cpp', 'h', 'hpp']:
                return 'cpp'
            elif ext in ['cs']:
                return 'csharp'
            elif ext in ['go']:
                return 'go'
            elif ext in ['rs']:
                return 'rust'
            elif ext in ['swift']:
                return 'swift'
            elif ext in ['php']:
                return 'php'
            elif ext in ['rb']:
                return 'ruby'
                
            # Veri formatları
            elif ext in ['pdf']:
                return 'pdf'
            elif ext in ['csv']:
                return 'csv'
            elif ext in ['json']:
                return 'json'
            elif ext in ['xml']:
                return 'xml'
        
        # İçeriği analiz et
        if not content or len(content) < 50:
            return 'plain'
        
        # HTML kontrolü
        if re.search(r'<\s*html|<\s*body|<\s*div|<\s*p\s*>|<\s*script', content, re.IGNORECASE):
            return 'html'
        
        # Markdown kontrolü
        if re.search(r'#{1,6}\s+|!\[.*?\]\(.*?\)|(?<!\*)\*{1,3}[^\*]+\*{1,3}(?!\*)|^>|^-\s+|^[0-9]+\.\s+', content, re.MULTILINE):
            return 'markdown'
        
        # JSON kontrolü
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                import json
                json.loads(content)
                return 'json'
            except:
                pass
        
        # XML kontrolü
        if re.search(r'<\?xml|<[a-zA-Z][a-zA-Z0-9]*(\s+[^>]*)?>(.*?)</[a-zA-Z][a-zA-Z0-9]*>', content):
            return 'xml'
        
        # CSV kontrolü
        if re.search(r'^(?:[\w\s]+,){2,}[\w\s]+$', content, re.MULTILINE):
            return 'csv'
        
        # Python kontrolü
        if re.search(r'\bdef\s+\w+|class\s+\w+|import\s+|from\s+\w+\s+import', content):
            return 'python'
        
        # JavaScript kontrolü
        if re.search(r'\bfunction\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+|\bimport\s+|export\s+|=>|React', content):
            return 'javascript'
        
        # TypeScript kontrolü
        if re.search(r':\s*(\w+|{[^}]*}|\[[^\]]*\])\s*[,=]|interface\s+\w+|type\s+\w+\s*=', content):
            return 'typescript'
        
        # Diğer kodlar için basit kontrol
        if re.search(r'(\{|\}|;|\bpublic\b|\bprivate\b|\bclass\b|\bvoid\b|\bfunc\b|\blet\b|\bvar\b)', content):
            return 'code'
        
        # Varsayılan düz metin
        return 'plain'
    
    def split_document(
        self, 
        content: str, 
        document_type: Optional[str] = None,
        file_extension: str = '',
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Belgeyi parçalara böl
        
        Args:
            content: Belge içeriği
            document_type: Belge türü (belirtilmezse otomatik algılanır)
            file_extension: Dosya uzantısı (belge türü algılama için ipucu)
            chunk_size: Parça boyutu (belirtilmezse varsayılan kullanılır)
            chunk_overlap: Örtüşen parça boyutu (belirtilmezse varsayılan kullanılır)
            metadata: Parçalara eklenecek meta veriler
            
        Returns:
            List[Dict[str, Any]]: Parçalar listesi (içerik ve meta veriler)
        """
        # Parametreleri hazırla
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        metadata = metadata or {}
        
        # Belge türünü belirleme
        if not document_type:
            document_type = self.get_document_type(content, file_extension)
        
        # Bölücü oluştur
        splitter_fn = self.text_types.get(document_type, self._create_text_splitter)
        splitter = splitter_fn(chunk_size, chunk_overlap)
        
        # Belgeye özel önişleme
        if document_type == 'csv':
            # CSV için özel işleme: başlık algılama ve sütunları koruma
            content = self._preprocess_csv(content)
        elif document_type == 'json':
            # JSON için özel işleme: formatı koruma
            content = self._preprocess_json(content)
        elif document_type == 'pdf':
            # PDF özel işleme: sayfa ve bölüm işaretlerini koru
            content = self._preprocess_pdf_text(content)
        
        # Belgeyi böl
        try:
            # Langchain text_splitter için uyumlu format
            from langchain.docstore.document import Document as LangchainDocument
            
            langchain_doc = LangchainDocument(page_content=content, metadata=metadata)
            docs = splitter.split_documents([langchain_doc])
            
            # Sonuçları formatlı
            result = []
            for i, doc in enumerate(docs):
                # Parça meta verilerini güncelle
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    'chunk_index': i,
                    'document_type': document_type
                })
                
                # Düzenli çıktı formatı
                result.append({
                    'content': doc.page_content,
                    'metadata': chunk_metadata
                })
            
            return result
        
        except ImportError:
            # Langchain yoksa düz bölme algoritması kullan
            logger.warning("Langchain not available, using simple text splitting")
            
            # Basit bölme
            chunks = self._simple_split_text(content, chunk_size, chunk_overlap)
            
            # Sonuçları formatlı
            result = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_index': i,
                    'document_type': document_type
                })
                
                result.append({
                    'content': chunk,
                    'metadata': chunk_metadata
                })
            
            return result
        
    def _simple_split_text(
        self, 
        text: str, 
        chunk_size: int, 
        chunk_overlap: int
    ) -> List[str]:
        """
        Temel metin bölme algoritması
        """
        # Metni paragraf ve cümlelere böl
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ''
        
        for para in paragraphs:
            # Paragraf zaten çok büyükse cümlelere böl
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                        if current_chunk:
                            current_chunk += ' '
                        current_chunk += sentence
                    else:
                        # Mevcut chunk'ı kaydet
                        if current_chunk:
                            chunks.append(current_chunk)
                            
                            # Örtüşme miktarını hesapla
                            overlap_content = self._get_overlap(current_chunk, chunk_overlap)
                            current_chunk = overlap_content + sentence
                        else:
                            # Cümle çok büyükse parçalayarak ekle
                            while len(sentence) > chunk_size:
                                chunks.append(sentence[:chunk_size])
                                sentence = sentence[chunk_size-chunk_overlap:]
                            
                            current_chunk = sentence
            else:
                # Normal boyuttaki paragrafı ekle
                if len(current_chunk) + len(para) + 2 <= chunk_size:
                    if current_chunk:
                        current_chunk += '\n\n'
                    current_chunk += para
                else:
                    # Mevcut chunk'ı kaydet
                    if current_chunk:
                        chunks.append(current_chunk)
                        
                        # Örtüşme miktarını hesapla
                        overlap_content = self._get_overlap(current_chunk, chunk_overlap)
                        current_chunk = overlap_content + para
                    else:
                        current_chunk = para
        
        # Son chunk'ı da kaydet
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_overlap(self, text: str, overlap_size: int) -> str:
        """
        Metin sonundan örtüşme içeriğini al
        """
        # Karakter sayısına göre değil sözcük sayısına göre örtüşme al
        words = text.split()
        
        if not words:
            return ""
        
        # Yaklaşık karakter sayısına denk gelen sözcük sayısını hesapla
        total_chars = sum(len(word) for word in words)
        chars_per_word = total_chars / len(words) if words else 5  # varsayılan
        
        word_count = int(overlap_size / chars_per_word)
        word_count = min(word_count, len(words))
        
        return ' '.join(words[-word_count:]) + ' ' if word_count > 0 else ''
    
    def _preprocess_csv(self, content: str) -> str:
        """
        CSV içeriğini bölmeye hazırla
        """
        lines = content.split('\n')
        
        if not lines:
            return content
        
        # Başlık satırını algıla
        header = lines[0]
        
        # Her bölünme bloğuna başlığı ekle
        result = []
        chunk_size = 100  # Satır sayısı
        
        for i in range(1, len(lines), chunk_size):
            chunk_lines = lines[i:i+chunk_size]
            result.append(header + '\n' + '\n'.join(chunk_lines))
        
        return '\n\n'.join(result)
    
    def _preprocess_json(self, content: str) -> str:
        """
        JSON içeriğini bölmeye hazırla
        """
        try:
            import json
            
            # JSON'u parse et
            data = json.loads(content)
            
            # Dizi ise
            if isinstance(data, list):
                # Elemanları grupla
                result = []
                group_size = 50  # Eleman sayısı
                
                for i in range(0, len(data), group_size):
                    chunk = data[i:i+group_size]
                    result.append(json.dumps(chunk, indent=2))
                
                return '\n\n'.join(result)
            
            # Nesne ise ve özellikler varsa
            if isinstance(data, dict):
                # Özellik sayısına göre bölme
                result = []
                keys = list(data.keys())
                group_size = 20  # Özellik sayısı
                
                for i in range(0, len(keys), group_size):
                    chunk_keys = keys[i:i+group_size]
                    chunk = {k: data[k] for k in chunk_keys}
                    result.append(json.dumps(chunk, indent=2))
                
                return '\n\n'.join(result)
        
        except:
            pass
        
        # Parse edemediysek orijinal içeriği döndür
        return content
    
    def _preprocess_pdf_text(self, content: str) -> str:
        """
        PDF metin içeriğini sayfa ve bölüm işaretleriyle işle
        """
        # Sayfa işaretlerini algıla ve koru
        content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)  # Tek satır sonlarını boşluğa çevir
        
        # Sayfa işaretleri: "Page X" veya "- X -" gibi
        page_markers = re.findall(r'\bPage\s+\d+\b|\b-\s*\d+\s*-\b', content)
        
        # Bölüm işaretleri: 1., 1.1., A., I. gibi
        section_pattern = r'\n(?:\d+\.(?:\d+\.)*|\w+\.)\s+[A-Z][a-zA-Z0-9]+'
        section_markers = re.findall(section_pattern, content)
        
        # Sayfa ve bölüm işaretlerini büyük ayraçlar ekleyerek güçlendir
        for marker in page_markers:
            content = content.replace(marker, f"\n\n{marker}\n\n")
        
        for marker in section_markers:
            # İlk \n'yi koru ama sonrasında boş satırlar ekle
            new_marker = marker[0] + "\n\n" + marker[1:]
            content = content.replace(marker, new_marker)
        
        return content


class SmartDocumentChunker(DocumentChunker):
    """
    Akıllı belge bölümleme sistemi
    
    Dokümanın semantik yapısını analiz ederek daha anlamlı parçalar oluşturur
    """
    
    def __init__(self):
        """SmartDocumentChunker başlat"""
        super().__init__()
        
        # Gelişmiş bölümlendirme için ayarlar
        self.max_section_length = 2000  # Maksimum bölüm uzunluğu
        self.min_section_length = 100   # Minimum anlamlı bölüm uzunluğu
    
    def split_document(
        self, 
        content: str, 
        document_type: Optional[str] = None,
        file_extension: str = '',
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Belgeyi akıllı bir şekilde parçalara böl
        
        Args:
            content: Belge içeriği
            document_type: Belge türü (belirtilmezse otomatik algılanır)
            file_extension: Dosya uzantısı (belge türü algılama için ipucu)
            chunk_size: Parça boyutu (belirtilmezse varsayılan kullanılır)
            chunk_overlap: Örtüşen parça boyutu (belirtilmezse varsayılan kullanılır)
            metadata: Parçalara eklenecek meta veriler
            
        Returns:
            List[Dict[str, Any]]: Parçalar listesi (içerik ve meta veriler)
        """
        # Parametreleri hazırla
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        metadata = metadata or {}
        
        # Belge türünü belirleme
        if not document_type:
            document_type = self.get_document_type(content, file_extension)
        
        # Belge türüne göre akıllı bölümleme stratejisini seç
        if document_type == 'markdown':
            return self._split_markdown_smart(content, chunk_size, chunk_overlap, metadata)
        elif document_type == 'html':
            return self._split_html_smart(content, chunk_size, chunk_overlap, metadata)
        elif document_type in ('python', 'javascript', 'typescript', 'java', 'cpp', 'csharp', 'go', 'rust'):
            return self._split_code_smart(content, document_type, chunk_size, chunk_overlap, metadata)
        elif document_type == 'pdf':
            return self._split_pdf_smart(content, chunk_size, chunk_overlap, metadata)
        else:
            # Diğer türler için temel bölümleme kullan
            return super().split_document(content, document_type, file_extension, chunk_size, chunk_overlap, metadata)
    
    def _split_markdown_smart(
        self,
        content: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Markdown içeriğini başlık ve bölümlere göre akıllıca böl
        """
        # Başlık örüntüsü: # Title, ## Subtitle vb.
        heading_pattern = re.compile(r'^(#{1,6})\s+(.*?)$', re.MULTILINE)
        
        # Başlıkları ve konumlarını bul
        headings = []
        for match in heading_pattern.finditer(content):
            level = len(match.group(1))  # Başlık seviyesi (# sayısı)
            title = match.group(2).strip()
            position = match.start()
            headings.append({
                'level': level,
                'title': title,
                'position': position
            })
        
        # Hiç başlık bulunamadıysa, normal bölme
        if not headings:
            return super().split_document(content, 'markdown', '', chunk_size, chunk_overlap, metadata)
        
        # Bölümleri oluştur
        sections = []
        for i, heading in enumerate(headings):
            start_pos = heading['position']
            end_pos = headings[i+1]['position'] if i < len(headings) - 1 else len(content)
            
            section_title = heading['title']
            section_level = heading['level']
            section_content = content[start_pos:end_pos]
            
            # Bölüm meta verilerini güncelle
            section_metadata = metadata.copy()
            section_metadata.update({
                'section_title': section_title,
                'section_level': section_level
            })
            
            # Bölüm uzunluğu yeterli ise ekle
            if len(section_content) >= self.min_section_length:
                # Bölüm çok büyükse daha fazla böl
                if len(section_content) > self.max_section_length:
                    # Alt bölümlere böl
                    sub_chunks = self._simple_split_text(section_content, chunk_size, chunk_overlap)
                    for j, sub_chunk in enumerate(sub_chunks):
                        sections.append({
                            'content': sub_chunk,
                            'metadata': {
                                **section_metadata,
                                'chunk_index': j,
                                'document_type': 'markdown',
                                'sub_section': f"{section_title} (Part {j+1}/{len(sub_chunks)})"
                            }
                        })
                else:
                    # Normal bölüm ekle
                    sections.append({
                        'content': section_content,
                        'metadata': {
                            **section_metadata,
                            'chunk_index': len(sections),
                            'document_type': 'markdown'
                        }
                    })
        
        return sections
    
    def _split_html_smart(
        self,
        content: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        HTML içeriğini anlamlı DOM elemanlarına göre böl
        """
        try:
            from bs4 import BeautifulSoup
            
            # HTML'i parse et
            soup = BeautifulSoup(content, 'html.parser')
            
            # Ana bölümleri bulma (article, section, main, div vb.)
            main_sections = []
            
            # Potansiyel ana içerik elemanları
            main_selectors = [
                'article', 'main', 'section', 'div.content', 'div.main', 
                'div#content', 'div#main'
            ]
            
            # Ana içeriği bul
            for selector in main_selectors:
                elements = soup.select(selector)
                if elements:
                    main_sections.extend(elements)
                    break
            
            # Ana içerik bulunamadıysa h1, h2, h3 vb başlıklara göre böl
            if not main_sections:
                headers = soup.find_all(['h1', 'h2', 'h3'])
                
                if headers:
                    # Başlıkları kullanarak bölümler oluştur
                    for i, header in enumerate(headers):
                        section = {'header': header}
                        
                        # Başlıktan sonraki içeriği toplama
                        content_elements = []
                        current = header.next_sibling
                        
                        # Bir sonraki başlığa kadar içeriği topla
                        while current and (i == len(headers) - 1 or current != headers[i+1]):
                            if current.name and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                content_elements.append(current)
                            current = current.next_sibling
                        
                        section['content'] = content_elements
                        main_sections.append(section)
            
            # Bölüm bulunamadıysa normal bölme kullan
            if not main_sections:
                return super().split_document(content, 'html', '', chunk_size, chunk_overlap, metadata)
            
            # Bölümleri işle ve çıkışı hazırla
            chunks = []
            for i, section in enumerate(main_sections):
                # Metin içeriğini al
                section_title = ''
                section_text = ''
                
                if isinstance(section, dict):  # Başlık bazlı bölüm
                    section_title = section['header'].get_text().strip()
                    section_content = ''.join(str(elem) for elem in section['content'])
                    section_text = BeautifulSoup(section_content, 'html.parser').get_text()
                else:  # DOM element
                    # Başlık içeriyor mu?
                    header = section.find(['h1', 'h2', 'h3'])
                    if header:
                        section_title = header.get_text().strip()
                    
                    section_text = section.get_text()
                
                # Bölüm meta verilerini güncelle
                section_metadata = metadata.copy()
                if section_title:
                    section_metadata['section_title'] = section_title
                
                # Bölüm çok büyükse alt bölümlere ayır
                if len(section_text) > chunk_size:
                    sub_chunks = self._simple_split_text(section_text, chunk_size, chunk_overlap)
                    
                    for j, sub_chunk in enumerate(sub_chunks):
                        chunks.append({
                            'content': sub_chunk,
                            'metadata': {
                                **section_metadata,
                                'chunk_index': len(chunks),
                                'document_type': 'html',
                                'sub_section': j + 1
                            }
                        })
                else:
                    # Bölüm yeterince küçükse doğrudan ekle
                    chunks.append({
                        'content': section_text,
                        'metadata': {
                            **section_metadata,
                            'chunk_index': len(chunks),
                            'document_type': 'html'
                        }
                    })
            
            return chunks
            
        except ImportError:
            logger.warning("BeautifulSoup not available, using simple HTML splitting")
            return super().split_document(content, 'html', '', chunk_size, chunk_overlap, metadata)
        except Exception as e:
            logger.error(f"Error in smart HTML splitting: {str(e)}")
            return super().split_document(content, 'html', '', chunk_size, chunk_overlap, metadata)
    
    def _split_code_smart(
        self,
        content: str,
        language: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Kaynak kodunu mantıksal birimler (sınıflar, fonksiyonlar) temelinde böl
        """
        # Dil bazlı düzenli ifadeleri belirle
        patterns = {
            'python': {
                # Class ve fonksiyon tanımları
                'class': r'class\s+(\w+)(?:\([^)]*\))?:',
                'function': r'def\s+(\w+)(?:\([^)]*\))?:',
                'comment': r'(?:""".*?"""|\'\'\'.*?\'\'\'|#.*?$)',
            },
            'javascript': {
                'class': r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s*{)',
                'function': r'(?:function\s+(\w+)|(\w+)\s*=\s*\(?(?:async)?\s*function|\(.*?\)\s*=>)|(\w+)\s*\([^)]*\)\s*{',
                'comment': r'(?://.*?$|/\*.*?\*/)',
            },
            'typescript': {
                'class': r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s