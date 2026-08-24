export type Page = 'studio' | 'voices' | 'history' | 'settings'

export interface Engine {
  id: string
  name: string
  available: boolean
  reason?: string
  capabilities: {
    voice_cloning: boolean
    presets: boolean
    accents: string[]
    development_only?: boolean
  }
}

export interface Voice {
  id: string
  name: string
  engine: string
  accent: string
  kind: 'preset' | 'cloned'
  created_at: string
}

export interface Phrase {
  phrase_index: number
  text: string
  source_start: number
  source_end: number
  pause_after_ms: number
  start_time?: number
  end_time?: number
  status: string
}

export interface Generation {
  id: string
  title: string
  raw_text?: string
  normalized_text?: string
  engine: string
  voice_id?: string
  settings?: Record<string, unknown>
  status: 'queued' | 'processing' | 'complete' | 'failed' | 'cancelled' | 'interrupted'
  progress: number
  error?: string
  duration?: number
  created_at: string
  updated_at: string
  phrases?: Phrase[]
  audio: { wav?: string; mp3?: string }
}

export interface Health {
  database: string
  data_directory: string
  disk_free: number
  last_backup?: Backup
  engines: Engine[]
}

export interface Backup {
  id: string
  path: string
  kind: string
  size_bytes: number
  integrity_ok: number | boolean
  created_at: string
}

