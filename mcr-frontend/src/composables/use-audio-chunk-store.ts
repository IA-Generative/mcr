import { openDB, type IDBPDatabase } from 'idb';

const DB_NAME = 'mcr-audio-chunks';
const DB_VERSION = 1;
const STORE_NAME = 'audio-chunks';

export interface AudioChunkRecord {
  id?: number;
  meetingId: number;
  filename: string;
  blob: Blob;
  status: 'pending' | 'uploaded';
  createdAt: number;
}

export type AudioChunkRecordCreationData = Omit<AudioChunkRecord, 'id' | 'createdAt' | 'status'>;

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const store = db.createObjectStore(STORE_NAME, {
          keyPath: 'id',
          autoIncrement: true,
        });
        store.createIndex('by-meetingId', 'meetingId');
      },
    });
  }
  return dbPromise;
}

/** @internal — exposed for tests only */
export async function _resetDb() {
  if (dbPromise) {
    const db = await dbPromise;
    db.close();
    dbPromise = null;
  }
}

async function addChunk(chunk: AudioChunkRecordCreationData): Promise<number> {
  const db = await getDb();
  const record: Omit<AudioChunkRecord, 'id'> = {
    ...chunk,
    status: 'pending',
    createdAt: Date.now(),
  };
  return (await db.add(STORE_NAME, record)) as number;
}

async function markChunkUploaded(id: number): Promise<void> {
  const db = await getDb();
  const record = await db.get(STORE_NAME, id);
  if (!record) return;
  record.status = 'uploaded';
  await db.put(STORE_NAME, record);
}

async function getPendingChunksForMeeting(meetingId: number): Promise<AudioChunkRecord[]> {
  const db = await getDb();
  const all = await db.getAllFromIndex(STORE_NAME, 'by-meetingId', meetingId);
  return all.filter((r: AudioChunkRecord) => r.status === 'pending');
}

async function getChunkCountForMeeting(meetingId: number): Promise<number> {
  const db = await getDb();
  const all = await db.getAllFromIndex(STORE_NAME, 'by-meetingId', meetingId);
  return all.length;
}

export function useAudioChunkStore() {
  return {
    addChunk,
    markChunkUploaded,
    getChunkCountForMeeting,
    getPendingChunksForMeeting,
  };
}
