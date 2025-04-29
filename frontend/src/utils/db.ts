// Last reviewed: 2025-04-29 13:36:58 UTC (User: TeeksssMobil)
import { openDB, DBSchema, IDBPDatabase } from 'idb';

// IndexedDB şeması
interface RagBaseDB extends DBSchema {
  documents: {
    key: number;
    value: {
      id: number;
      title: string;
      content?: string;
      summary?: string;
      tags?: string[];
      createdAt: string;
      updatedAt: string;
      path?: string;
      isLocal: boolean;
      localUpdated?: boolean;
    };
    indexes: {
      'by-title': string;
      'by-tags': string[];
      'by-updated': string;
      'by-local': boolean;
    };
  };
  settings: {
    key: string;
    value: any;
  };
  searchHistory: {
    key: number;
    value: {
      id: number;
      query: string;
      timestamp: string;
      resultCount?: number;
    };
    indexes: {
      'by-timestamp': string;
    };
  };
  pendingUploads: {
    key: string;
    value: {
      id: string;
      file: File;
      metadata: {
        title: string;
        description?: string;
        tags?: string[];
        createdAt: string;
      };
      status: 'pending' | 'error' | 'uploading' | 'completed';
      progress: number;
      error?: string;
    };
  };
  syncQueue: {
    key: number;
    value: {
      id: number;
      action: 'create' | 'update' | 'delete';
      entityType: 'document' | 'collection' | 'user';
      entityId: number | string;
      payload: any;
      timestamp: string;
      retryCount: number;
      status: 'pending' | 'processing' | 'error';
      error?: string;
    };
    indexes: {
      'by-status': string;
    };
  };
}

// Veritabanı versiyonu - her şema değişikliğinde arttırılmalı
const DB_VERSION = 1;
const DB_NAME = 'ragbase-db';

// DB bağlantısı için referans
let dbPromise: Promise<IDBPDatabase<RagBaseDB>>;

// Veritabanını aç veya oluştur
export async function openDatabase() {
  if (!dbPromise) {
    dbPromise = openDB<RagBaseDB>(DB_NAME, DB_VERSION, {
      upgrade(db, oldVersion, newVersion, transaction) {
        // Yeni veritabanı oluşturma
        if (oldVersion === 0) {
          // Documents store
          const documentsStore = db.createObjectStore('documents', {
            keyPath: 'id'
          });
          documentsStore.createIndex('by-title', 'title', { unique: false });
          documentsStore.createIndex('by-tags', 'tags', { unique: false, multiEntry: true });
          documentsStore.createIndex('by-updated', 'updatedAt', { unique: false });
          documentsStore.createIndex('by-local', 'isLocal', { unique: false });

          // Settings store
          db.createObjectStore('settings', {
            keyPath: 'key'
          });

          // Search history store
          const searchStore = db.createObjectStore('searchHistory', {
            keyPath: 'id',
            autoIncrement: true
          });
          searchStore.createIndex('by-timestamp', 'timestamp', { unique: false });

          // Pending uploads store
          db.createObjectStore('pendingUploads', {
            keyPath: 'id'
          });

          // Sync queue store
          const syncStore = db.createObjectStore('syncQueue', {
            keyPath: 'id',
            autoIncrement: true
          });
          syncStore.createIndex('by-status', 'status', { unique: false });
        }

        // Versiyon yükseltme işlemleri burada yapılır
        if (oldVersion < 1 && newVersion >= 1) {
          // v1'e özgü yükseltme işlemleri
        }
      }
    });
  }

  return dbPromise;
}

// Döküman işlemleri
export async function saveDocument(document: any) {
  const db = await openDatabase();
  document.isLocal = true;
  document.localUpdated = true;
  return db.put('documents', document);
}

export async function getDocument(id: number) {
  const db = await openDatabase();
  return db.get('documents', id);
}

export async function deleteDocument(id: number) {
  const db = await openDatabase();
  return db.delete('documents', id);
}

export async function getLocalDocuments() {
  const db = await openDatabase();
  return db.getAllFromIndex('documents', 'by-local', true);
}

export async function getLocalUpdatedDocuments() {
  const db = await openDatabase();
  const allDocs = await db.getAll('documents');
  return allDocs.filter(doc => doc.localUpdated);
}

// Ayarlar işlemleri
export async function saveSetting(key: string, value: any) {
  const db = await openDatabase();
  return db.put('settings', { key, value });
}

export async function getSetting(key: string) {
  const db = await openDatabase();
  const setting = await db.get('settings', key);
  return setting?.value;
}

// Arama geçmişi işlemleri
export async function saveSearch(query: string, resultCount?: number) {
  const db = await openDatabase();
  return db.add('searchHistory', {
    query,
    timestamp: new Date().toISOString(),
    resultCount
  });
}

export async function getRecentSearches(limit = 10) {
  const db = await openDatabase();
  const tx = db.transaction('searchHistory', 'readonly');
  const index = tx.store.index('by-timestamp');
  
  const searches = [];
  let cursor = await index.openCursor(null, 'prev'); // En yeniler önce
  
  while (cursor && searches.length < limit) {
    searches.push(cursor.value);
    cursor = await cursor.continue();
  }
  
  return searches;
}

// Yükleme kuyruğu işlemleri
export async function queueFileUpload(id: string, file: File, metadata: any) {
  const db = await openDatabase();
  return db.put('pendingUploads', {
    id,
    file,
    metadata: {
      ...metadata,
      createdAt: new Date().toISOString()
    },
    status: 'pending',
    progress: 0
  });
}

export async function updateUploadProgress(id: string, progress: number, status: 'pending' | 'uploading' | 'error' | 'completed', error?: string) {
  const db = await openDatabase();
  const upload = await db.get('pendingUploads', id);
  if (upload) {
    upload.progress = progress;
    upload.status = status;
    if (error) upload.error = error;
    return db.put('pendingUploads', upload);
  }
  return null;
}

export async function getPendingUploads() {
  const db = await openDatabase();
  return db.getAll('pendingUploads');
}

// Senkronizasyon kuyruğu işlemleri
export async function addToSyncQueue(action: 'create' | 'update' | 'delete', entityType: 'document' | 'collection' | 'user', entityId: number | string, payload: any) {
  const db = await openDatabase();
  return db.add('syncQueue', {
    action,
    entityType,
    entityId,
    payload,
    timestamp: new Date().toISOString(),
    retryCount: 0,
    status: 'pending'
  });
}

export async function updateSyncStatus(id: number, status: 'pending' | 'processing' | 'error', error?: string) {
  const db = await openDatabase();
  const item = await db.get('syncQueue', id);
  if (item) {
    item.status = status;
    if (error) item.error = error;
    if (status === 'error') item.retryCount += 1;
    return db.put('syncQueue', item);
  }
  return null;
}

export async function getPendingSyncItems() {
  const db = await openDatabase();
  return db.getAllFromIndex('syncQueue', 'by-status', 'pending');
}

export async function clearSyncItem(id: number) {
  const db = await openDatabase();
  return db.delete('syncQueue', id);
}

// Veritabanı yönetimi
export async function clearAllData() {
  const db = await openDatabase();
  const stores = ['documents', 'settings', 'searchHistory', 'pendingUploads', 'syncQueue'];
  const tx = db.transaction(stores, 'readwrite');
  
  await Promise.all([
    ...stores.map(store => tx.objectStore(store).clear()),
    tx.done
  ]);
  
  return true;
}

export async function exportData() {
  const db = await openDatabase();
  const stores = ['documents', 'settings', 'searchHistory'];
  const exportData: Record<string, any[]> = {};
  
  await Promise.all(stores.map(async (store) => {
    exportData[store] = await db.getAll(store as any);
  }));
  
  return exportData;
}

export async function importData(data: Record<string, any[]>) {
  const db = await openDatabase();
  const stores = Object.keys(data);
  
  for (const store of stores) {
    if (!['documents', 'settings', 'searchHistory'].includes(store)) continue;
    
    const tx = db.transaction(store as any, 'readwrite');
    const objectStore = tx.objectStore(store as any);
    
    await Promise.all([
      ...data[store].map(item => objectStore.put(item)),
      tx.done
    ]);
  }
  
  return true;
}