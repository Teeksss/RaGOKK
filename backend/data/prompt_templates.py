# Last reviewed: 2025-04-30 06:57:19 UTC (User: Teeksss)
DEFAULT_PROMPT_TEMPLATES = [
    # Tanım soruları için şablon
    {
        "name": "Definition Prompt Template",
        "description": "Tanım ve açıklama soruları için tasarlanmış şablon",
        "template": """Aşağıdaki konuyu veya terimi, verilen bağlam bilgilerine dayanarak detaylı bir şekilde açıklayın.
Temel unsurları, önemli kavramları ve örnekleri içeren kapsamlı bir tanım oluşturun.

Bağlam:
{{context}}

Tanımlanacak konu/terim: {{query}}

Kaynaklara referans vererek açıklayın (ör: [1], [2]). Yanıtınız şunları içermeli:
1. Kısa ve öz bir giriş tanımı
2. Ana unsurlar ve kavramsal açıklama 
3. Önemli noktaların veya örneklerin vurgulanması
4. Gerekiyorsa alternatif tanımlar veya bağlamlar

Yanıtınızı Markdown formatında oluşturunuz.""",
        "template_type": "definition",
        "is_active": True
    },
    
    # Prosedür soruları için şablon
    {
        "name": "Procedural Prompt Template",
        "description": "Adım adım talimatlar ve nasıl yapılır soruları için şablon",
        "template": """Aşağıdaki işlemin/görevin nasıl yapılacağını, verilen bağlam bilgilerine dayanarak adım adım açıklayın.

Bağlam:
{{context}}

Nasıl yapılır: {{query}}

Kaynaklara referans vererek açıklayın (ör: [1], [2]). Yanıtınız şunları içermeli:
1. Kısa bir genel bakış ve amaç açıklaması
2. Gerekli araçlar, koşullar veya ön hazırlıklar
3. Numaralandırılmış adımlar halinde prosedür
4. Önemli uyarılar, ipuçları veya alternatif yaklaşımlar
5. Varsa yaygın sorunlar ve çözümleri

Adımları net, kısa ve anlaşılır tutun. Yanıtınızı Markdown formatında oluşturunuz.""",
        "template_type": "procedural",
        "is_active": True
    },
    
    # Analitik sorular için şablon
    {
        "name": "Analytical Prompt Template",
        "description": "Karşılaştırma ve analiz içeren sorular için şablon",
        "template": """Aşağıdaki konuyu, verilen bağlam bilgilerine dayanarak derinlemesine analiz edin/karşılaştırın.

Bağlam:
{{context}}

Analiz edilecek/Karşılaştırılacak konu: {{query}}

Kaynaklara referans vererek (ör: [1], [2]) analiz yapın. Yanıtınız şunları içermeli:
1. Konunun genel çerçevesi ve önemi
2. Farklı bakış açıları veya yaklaşımlar
3. Güçlü ve zayıf yönler, benzerlikler ve farklılıklar
4. Destekleyici kanıtlar ve örnekler
5. Sentez ve sonuç

Analizinizi dengeli, objektif ve kapsamlı tutun. Yanıtınızı Markdown formatında oluşturunuz.""",
        "template_type": "analytical",
        "is_active": True
    },
    
    # Liste soruları için şablon
    {
        "name": "List Prompt Template",
        "description": "Liste ve sıralama içeren sorular için şablon",
        "template": """Aşağıdaki konuyla ilgili kapsamlı bir liste oluşturun, verilen bağlam bilgilerini kullanarak.

Bağlam:
{{context}}

Listelenecek öğeler: {{query}}

Kaynaklara referans vererek (ör: [1], [2]) kapsamlı bir liste hazırlayın. Yanıtınız şunları içermeli:
1. Kısa bir giriş ve listenin amacı
2. Belirli bir düzende (ör: kronolojik, önem derecesi) kategorize edilmiş öğeler
3. Gerektiğinde her öğe için kısa açıklamalar
4. Listedeki öğelerin belirleyici özellikleri

Listenizi tam ve düzenli tutun. Yanıtınızı Markdown formatında oluşturunuz.""",
        "template_type": "list",
        "is_active": True
    },
    
    # Varsayılan şablon
    {
        "name": "Default Prompt Template",
        "description": "Genel amaçlı varsayılan şablon",
        "template": """Aşağıdaki soruya, verilen bağlam bilgilerine dayanarak yanıt verin.
Bağlam bilgilerinde bulamazsan "Bu soruya yanıt vermek için yeterli bilgi bulunamadı" diyebilirsin.

Bağlam:
{{context}}

Soru: {{query}}

Kaynaklara referans vererek yanıtlayın. Örneğin: "... [1]" veya "... [2]". Yanıtınız Markdown formatında olmalıdır.""",
        "template_type": "default",
        "is_active": True
    }
]