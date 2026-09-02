export type Page = 'studio' | 'voices' | 'history' | 'settings'
export type BreezePage = 'studio' | 'lab' | 'voices' | 'history' | 'settings'

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

export interface BreezeVoice {
  id: string
  name: string
  kind: 'designed' | 'cloned'
  language: 'en' | 'zh'
  accent_direction: string
  description: string
  reference_text?: string
  seed: number
  cfg_scale: number
  created_at: string
  updated_at: string
}

export interface BreezeGeneration extends Generation {
  mode: 'design' | 'clone' | 'direction'
  language: 'en' | 'zh'
  accent_direction: string
  direction: string
  model_variant: 'mixed-4bit'
  generation_seconds?: number
  real_time_factor?: number
}

export interface BreezeCapabilities {
  id: string
  name: string
  available: boolean
  reason?: string
  modes: string[]
  languages: {id: 'en' | 'zh'; name: string}[]
  english_directions: string[]
  capabilities: Record<string, unknown>
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
