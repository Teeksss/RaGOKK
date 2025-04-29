# Last reviewed: 2025-04-29 12:57:38 UTC (User: Teeksssprometheus)
from typing import List, Dict, Any, Optional, Tuple, Union
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..db.models import Collection, UserCollectionPermission
from ..schemas.collection import CollectionCreate, CollectionUpdate

class CollectionRepository:
    """
    Doküman koleksiyonları ve klasörler için veritabanı işlemleri
    
    Özellikler:
    - Hiyerarşik klasör yapısı desteği
    - Paylaşım ve izin yönetimi
    - Meta veri saklama
    - Etiket desteği
    """
    
    async def create_collection(self, db: AsyncSession, data: CollectionCreate, user_id: str) -> Collection:
        """
        Yeni bir koleksiyon oluşturur
        
        Args:
            db: Veritabanı oturumu
            data: Koleksiyon bilgileri
            user_id: Koleksiyonu oluşturan kullanıcı
            
        Returns:
            Collection: Oluşturulan koleksiyon
        """
        # Parent kontrolü
        parent_id = data.parent_id
        if parent_id:
            # Parent koleksiyon var mı kontrol et
            parent_query = """
            SELECT * FROM collections WHERE id = :parent_id
            """
            parent_result = await db.execute(text(parent_query), {"parent_id": parent_id})
            parent = parent_result.fetchone()
            
            if not parent:
                raise ValueError(f"Parent collection with ID {parent_id} not found")
            
            # Kullanıcının bu parent klasöre yazma yetkisi var mı?
            if parent.owner_id != user_id:
                permission_query = """
                SELECT permission_type FROM user_collection_permissions
                WHERE collection_id = :collection_id AND user_id = :user_id
                """
                permission_result = await db.execute(
                    text(permission_query), 
                    {"collection_id": parent_id, "user_id": user_id}
                )
                permission = permission_result.fetchone()
                
                if not permission or permission.permission_type not in ['write', 'admin']:
                    raise ValueError(f"You don't have write permission for parent collection {parent_id}")
            
            # Hiyerarşi döngüsü kontrolü
            await self._check_hierarchy_loop(db, parent_id, None)
        
        # Koleksiyonu oluştur
        query = """
        INSERT INTO collections
            (name, description, parent_id, owner_id, is_public, icon, color, sort_order, metadata, created_at, updated_at)
        VALUES
            (:name, :description, :parent_id, :owner_id, :is_public, :icon, :color, :sort_order, :metadata, NOW(), NOW())
        RETURNING *
        """
        
        # Metadata'yı JSON olarak dönüştür
        metadata_json = json.dumps(data.metadata) if data.metadata else None
        
        # Sorguyu çalıştır
        result = await db.execute(
            text(query),
            {
                "name": data.name,
                "description": data.description,
                "parent_id": data.parent_id,
                "owner_id": user_id,
                "is_public": data.is_public,
                "icon": data.icon,
                "color": data.color,
                "sort_order": data.sort_order or 0,
                "metadata": metadata_json
            }
        )
        
        collection = result.fetchone()
        
        # Etiketleri ekle
        if data.tags:
            for tag in data.tags:
                await self._add_tag_to_collection(db, collection.id, tag)
        
        return collection
    
    async def _check_hierarchy_loop(self, db: AsyncSession, parent_id: int, collection_id: Optional[int]) -> bool:
        """
        Koleksiyon hiyerarşisinde döngü olup olmadığını kontrol eder
        
        Args:
            db: Veritabanı oturumu
            parent_id: Parent koleksiyon ID
            collection_id: Kontrol edilen koleksiyon ID (None ise yeni koleksiyon)
            
        Returns:
            bool: Döngü yoksa True
            
        Raises:
            ValueError: Döngü tespit edilirse
        """
        # Koleksiyon ile parent aynı ise döngü var
        if collection_id is not None and collection_id == parent_id:
            raise ValueError("Collection cannot be its own parent")
        
        # Parent koleksiyonun üst hiyerarşisini kontrol et
        current_parent_id = parent_id
        visited = set([parent_id])
        
        while current_parent_id is not None:
            query = "SELECT parent_id FROM collections WHERE id = :parent_id"
            result = await db.execute(text(query), {"parent_id": current_parent_id})
            parent_row = result.fetchone()
            
            if not parent_row:
                break
                
            current_parent_id = parent_row.parent_id
            
            # Döngü kontrolü
            if current_parent_id is not None:
                if current_parent_id == collection_id:
                    raise ValueError("Detected hierarchy loop in collection structure")
                
                if current_parent_id in visited:
                    raise ValueError("Detected existing hierarchy loop in collection structure")
                
                visited.add(current_parent_id)
        
        return True
    
    async def _add_tag_to_collection(self, db: AsyncSession, collection_id: int, tag_name: str) -> Dict[str, Any]:
        """
        Koleksiyona etiket ekler
        
        Args:
            db: Veritabanı oturumu
            collection_id: Koleksiyon ID
            tag_name: Etiket adı
            
        Returns:
            Dict[str, Any]: Etiket bilgileri
        """
        # Etiket var mı kontrol et, yoksa oluştur
        tag_query = "SELECT id FROM tags WHERE name = :tag_name"
        tag_result = await db.execute(text(tag_query), {"tag_name": tag_name})
        tag_row = tag_result.fetchone()
        
        tag_id = None
        if tag_row:
            tag_id = tag_row.id
        else:
            # Yeni etiket oluştur
            insert_tag_query = "INSERT INTO tags (name, created_at) VALUES (:tag_name, NOW()) RETURNING id"
            tag_result = await db.execute(text(insert_tag_query), {"tag_name": tag_name})
            tag_id = tag_result.fetchone().id
        
        # Koleksiyon ve etiket ilişkisini ekle
        relation_query = """
        INSERT INTO collection_tags (collection_id, tag_id, created_at)
        VALUES (:collection_id, :tag_id, NOW())
        ON CONFLICT (collection_id, tag_id) DO NOTHING
        """
        
        await db.execute(
            text(relation_query),
            {
                "collection_id": collection_id,
                "tag_id": tag_id
            }
        )
        
        return {
            "collection_id": collection_id,
            "tag_id": tag_id,
            "tag_name": tag_name
        }
    
    async def update_collection(self, db: AsyncSession, collection_id: int, data: CollectionUpdate, user_id: str) -> Optional[Collection]:
        """
        Koleksiyonu günceller
        
        Args:
            db: Veritabanı oturumu
            collection_id: Koleksiyon ID
            data: Güncellenecek veriler
            user_id: İsteği yapan kullanıcı ID
            
        Returns:
            Optional[Collection]: Güncellenen koleksiyon veya None
        """
        # Koleksiyon var mı ve kullanıcı yetkili mi kontrol et
        collection = await self.get_collection(db, collection_id)
        if not collection:
            return None
            
        # Yetki kontrolü
        has_permission = await self.check_user_permission(db, collection_id, user_id, "write")
        if not has_permission and collection["owner_id"] != user_id:
            raise ValueError(f"User {user_id} doesn't have write permission for collection {collection_id}")
        
        # Parent değişiyorsa hiyerarşi döngüsü kontrolü yap
        if data.parent_id is not None and data.parent_id != collection["parent_id"]:
            await self._check_hierarchy_loop(db, data.parent_id, collection_id)
        
        # Güncellenecek alanları topla
        update_fields = []
        params = {"collection_id": collection_id}
        
        if data.name is not None:
            update_fields.append("name = :name")
            params["name"] = data.name
            
        if data.description is not None:
            update_fields.append("description = :description")
            params["description"] = data.description
            
        if data.parent_id is not None:
            update_fields.append("parent_id = :parent_id")
            params["parent_id"] = data.parent_id
            
        if data.is_public is not None:
            update_fields.append("is_public = :is_public")
            params["is_public"] = data.is_public
            
        if data.icon is not None:
            update_fields.append("icon = :icon")
            params["icon"] = data.icon
            
        if data.color is not None:
            update_fields.append("color = :color")
            params["color"] = data.color
            
        if data.sort_order is not None:
            update_fields.append("sort_order = :sort_order")
            params["sort_order"] = data.sort_order
            
        if data.metadata is not None:
            update_fields.append("metadata = :metadata")
            params["metadata"] = json.dumps(data.metadata)
        
        # Güncellenecek alan yoksa hemen dön
        if not update_fields:
            return collection
            
        # Son güncelleme zamanını ekle
        update_fields.append("updated_at = NOW()")
        
        # Güncelleme sorgusu
        update_query = f"""
        UPDATE collections
        SET {", ".join(update_fields)}
        WHERE id = :collection_id
        RETURNING *
        """
        
        result = await db.execute(text(update_query), params)
        updated_collection = result.fetchone()
        
        # Etiketleri güncelle
        if data.tags is not None:
            # Mevcut etiketleri temizle
            await db.execute(
                text("DELETE FROM collection_tags WHERE collection_id = :collection_id"),
                {"collection_id": collection_id}
            )
            
            # Yeni etiketleri ekle
            for tag in data.tags:
                await self._add_tag_to_collection(db, collection_id, tag)
        
        return self._row_to_dict(updated_collection)
    
    async def delete_collection(self, db: AsyncSession, collection_id: int, user_id: str, recursive: bool = False) -> bool:
        """
        Koleksiyonu siler
        
        Args:
            db: Veritabanı oturumu
            collection_id: Koleksiyon ID
            user_id: İsteği yapan kullanıcı
            recursive: Alt koleksiyonları da sil
            
        Returns:
            bool: Başarılı ise True
        """
        # Koleksiyon var mı ve kullanıcı yetkili mi kontrol et
        collection = await self.get_collection(db, collection_id)
        if not collection:
            return False
            
        # Yetki kontrolü
        is_owner = collection["owner_id"] == user_id
        has_admin = await self.check_user_permission(db, collection_id, user_id, "admin")
        
        if not is_owner and not has_admin:
            raise ValueError(f"User {user_id} doesn't have delete permission for collection {collection_id}")
        
        # Alt koleksiyonları kontrol et
        children_query = "SELECT id FROM collections WHERE parent_id = :collection_id"
        children_result = await db.execute(text(children_query), {"collection_id": collection_id})
        children = children_result.fetchall()
        
        if children and not recursive:
            raise ValueError(f"Collection {collection_id} has sub-collections. Use recursive=True to delete them too.")
            
        # Alt koleksiyonları sil
        if children and recursive:
            for child in children:
                await self.delete_collection(db, child.id, user_id, recursive=True)
        
        # Koleksiyon içindeki dokümanları güncelle
        update_docs_query = """
        UPDATE documents
        SET collection_id = NULL, updated_at = NOW()
        WHERE collection_id = :collection_id
        """
        await db.execute(text(update_docs_query), {"collection_id": collection_id})
        
        # İlişkili verileri temizle
        # 1. Etiketler
        await db.execute(
            text("DELETE FROM collection_tags WHERE collection_id = :collection_id"),
            {"collection_id": collection_id}
        )
        
        # 2. İzinler
        await db.execute(
            text("DELETE FROM user_collection_permissions WHERE collection_id = :collection_id"),
            {"collection_id": collection_id}
        )
        
        # Koleksiyonu sil
        delete_query = "DELETE FROM collections WHERE id = :collection_id"
        await db.execute(text(delete_query), {"collection_id": collection_id})
        
        return True
    
    async def get_collection(self, db: AsyncSession, collection_id: int) -> Optional[Dict[str, Any]]:
        """
        Koleksiyon detaylarını getirir
        
        Args:
            db: Veritabanı oturumu
            collection_id: Koleksiyon ID
            
        Returns:
            Optional[Dict[str, Any]]: Koleksiyon bilgileri veya None
        """
        query = """
        SELECT c.*,
               array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) as tags
        FROM collections c
        LEFT JOIN collection_tags ct ON c.id = ct.collection_id
        LEFT JOIN tags t ON ct.tag_id = t.id
        WHERE c.id = :collection_id
        GROUP BY c.id
        """
        
        result = await db.execute(text(query), {"collection_id": collection_id})
        row = result.fetchone()
        
        if not row:
            return None
            
        collection_dict = self._row_to_dict(row)
        
        # Alt koleksiyonları say
        children_query = """
        SELECT COUNT(*) as child_count
        FROM collections
        WHERE parent_id = :collection_id
        """
        
        children_result = await db.execute(text(children_query), {"collection_id": collection_id})
        children_count = children_result.scalar()
        collection_dict["child_count"] = children_count or 0
        
        # İçerdiği doküman sayısını say
        documents_query = """
        SELECT COUNT(*) as document_count
        FROM documents
        WHERE collection_id = :collection_id
        """
        
        documents_result = await db.execute(text(documents_query), {"collection_id": collection_id})
        document_count = documents_result.scalar()
        collection_dict["document_count"] = document_count or 0
        
        return collection_dict
    
    async def get_collections(
        self, 
        db: AsyncSession,
        user_id: str,
        parent_id: Optional[int] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_public: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının erişebildiği koleksiyonları listeler
        
        Args:
            db: Veritabanı oturumu
            user_id: Kullanıcı ID
            parent_id: Üst klasör ID (None ise kök klasörler)
            search: Arama metni
            tags: Etiket filtreleri
            include_public: Herkese açık koleksiyonları dahil et
            
        Returns:
            List[Dict[str, Any]]: Koleksiyonlar listesi
        """
        base_query = """
        WITH accessible_collections AS (
            -- Kullanıcının sahibi olduğu koleksiyonlar
            SELECT c.*, 'owner' as permission_type
            FROM collections c
            WHERE c.owner_id = :user_id
            
            UNION
            
            -- Kullanıcıyla paylaşılmış koleksiyonlar
            SELECT c.*, ucp.permission_type
            FROM collections c
            JOIN user_collection_permissions ucp ON c.id = ucp.collection_id
            WHERE ucp.user_id = :user_id
            
            UNION
            
            -- Herkese açık koleksiyonlar (include_public=true ise)
            SELECT c.*, 'read' as permission_type
            FROM collections c
            WHERE c.is_public = true AND :include_public = true
        )
        SELECT c.*,
               array_agg(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) as tags,
               c.permission_type,
               COUNT(DISTINCT d.id) as document_count,
               COUNT(DISTINCT child.id) as child_count
        FROM accessible_collections c
        LEFT JOIN collection_tags ct ON c.id = ct.collection_id
        LEFT JOIN tags t ON ct.tag_id = t.id
        LEFT JOIN documents d ON d.collection_id = c.id
        LEFT JOIN collections child ON child.parent_id = c.id
        WHERE 1=1
        """
        
        params = {
            "user_id": user_id,
            "include_public": include_public
        }
        
        # Parent ID filtresi
        if parent_id is not None:
            base_query += " AND c.parent_id = :parent_id"
            params["parent_id"] = parent_id
        else:
            base_query += " AND c.parent_id IS NULL"
        
        # Arama filtresi
        if search:
            base_query += " AND (c.name ILIKE :search OR c.description ILIKE :search)"
            params["search"] = f"%{search}%"
        
        # Etiket filtresi
        if tags and len(tags) > 0:
            tag_placeholders = [f":tag_{i}" for i in range(len(tags))]
            tag_params = ", ".join(tag_placeholders)
            
            base_query += f"""
            AND EXISTS (
                SELECT 1 FROM collection_tags ct2
                JOIN tags t2 ON ct2.tag_id = t2.id
                WHERE ct2.collection_id = c.id AND t2.name IN ({tag_params})
            )
            """
            
            for i, tag in enumerate(tags):
                params[f"tag_{i}"] = tag
        
        # Gruplama ve sıralama
        base_query += """
        GROUP BY c.id, c.name, c.description, c.parent_id, c.owner_id, c.is_public, 
                 c.icon, c.color, c.sort_order, c.metadata, c.created_at, c.updated_at, c.permission_type
        ORDER BY c.sort_order ASC, c.name ASC
        """
        
        result = await db.execute(text(base_query), params)
        rows = result.fetchall()
        
        collections = [self._row_to_dict(row) for row in rows]
        return collections
    
    async def get_collection_breadcrumbs(self, db: AsyncSession, collection_id: int) -> List[Dict[str, Any]]:
        """
        Koleksiyon için breadcrumb (ekmek kırıntısı) yolunu getirir
        
        Args:
            db: Veritabanı oturumu
            collection_id: Koleksiyon ID
            
        Returns:
            List[Dict[str, Any]]: Üst klasör hiyerarşisi
        """
        query = """
        WITH RECURSIVE collection_path AS (
            -- Başlangıç koleksiyonu
            SELECT c.*, 0 as level
            FROM collections c
            WHERE c.id = :collection_id
            
            UNION ALL
            
            -- Üst koleksiyonları ekle
            SELECT c.*, cp.level + 1
            FROM collections c
            JOIN collection_path cp ON c.id = cp.parent_id
        )
        SELECT id, name, parent_id, level
        FROM collection_path
        ORDER BY level DESC  -- Kökten hedefe doğru sıralama
        """
        
        result = await db.execute(text(query), {"collection_id": collection_id})
        rows = result.fetchall()
        
        breadcrumbs = []
        for row in rows:
            breadcrumbs.append({
                "id": row.id,
                "name": row.name,
                "parent_id": row.parent_id
            })
            
        return breadcrumbs
    
    async def move_document_to_collection(
        self, 
        db: AsyncSession, 
        document_id: int, 
        collection_id: Optional[int], 
        user_id: str
    ) -> bool:
        """
        Dokümanı bir koleksiyona taşır
        
        Args:
            db: Veritabanı oturumu
            document_id: Doküman ID
            collection_id: Hedef koleksiyon ID (None ise kökten çıkar)
            user_id: İşlemi yapan kullanıcı ID
            
        Returns:
            bool: Başarılı ise True
        """
        # Doküman var mı ve kullanıcı yetkili mi kontrol et
        document_query = """
        SELECT * FROM documents WHERE id = :document_id
        """
        document_result = await db.execute(text(document_query), {"document_id": document_id})
        document = document_result.fetchone()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
            
        # Doküman üzerinde yazma yetkisi var mı?
        is_owner = document.owner_id == user_id
        has_write_access = False
        
        if not is_owner:
            perm_query = """
            SELECT permission_type FROM user_document_permissions
            WHERE document_id = :document_id AND user_id = :user_id
            """
            perm_result = await db.execute(text(perm_query), {"document_id": document_id, "user_id": user_id})
            perm = perm_result.fetchone()
            
            if perm and perm.permission_type in ['write', 'admin']:
                has_write_access = True
                
        if not is_owner and not has_write_access:
            raise ValueError(f"User {user_id} doesn't have write permission for document {document_id}")
        
        # Hedef koleksiyon kontrolü
        if collection_id is not None:
            collection = await self.get_collection(db, collection_id)
            if not collection:
                raise ValueError(f"Collection {collection_id} not