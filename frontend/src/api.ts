import type { Backup, BreezeCapabilities, BreezeGeneration, BreezeVoice, Engine, Generation, Health, Voice } from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const serverDetail = (await response.json()).detail
      if (typeof serverDetail === 'string') detail = serverDetail
      else if (Array.isArray(serverDetail)) detail = serverDetail.map(item => item.msg || JSON.stringify(item)).join('; ')
      else if (serverDetail) detail = JSON.stringify(serverDetail)
    } catch { /* ignore */ }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  engines: () => request<Engine[]>('/api/engines'),
  voices: () => request<Voice[]>('/api/voices'),
  generations: (q = '') => request<{items: Generation[]; total: number}>(`/api/generations?q=${encodeURIComponent(q)}`),
  generation: (id: string) => request<Generation>(`/api/generations/${id}`),
  createGeneration: (payload: Record<string, unknown>) => request<Generation>('/api/generations', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
  }),
  cancel: (id: string) => request(`/api/generations/${id}/cancel`, {method: 'POST'}),
  resume: (id: string) => request<Generation>(`/api/generations/${id}/resume`, {method: 'POST'}),
  deleteGeneration: (id: string) => request(`/api/generations/${id}`, {method: 'DELETE'}),
  createVoice: (data: FormData) => request<Voice>('/api/voices', {method: 'POST', body: data}),
  voicePreview: (id: string) => request<{voice_id: string; text: string; audio_url: string; cached: boolean}>(`/api/voices/${id}/preview`, {method: 'POST'}),
  deleteVoice: (id: string) => request(`/api/voices/${id}`, {method: 'DELETE'}),
  health: () => request<Health>('/api/system/health'),
  backups: () => request<Backup[]>('/api/backups'),
  createBackup: () => request<Backup>('/api/backups', {method: 'POST'}),
  restoreBackup: (id: string) => request(`/api/backups/${id}/restore`, {method: 'POST'}),
}

export const breezeApi = {
  capabilities: () => request<BreezeCapabilities>('/api/v2/capabilities'),
  voices: () => request<BreezeVoice[]>('/api/v2/voices'),
  generations: (q = '') => request<{items: BreezeGeneration[]; total: number}>(`/api/v2/generations?q=${encodeURIComponent(q)}`),
  generation: (id: string) => request<BreezeGeneration>(`/api/v2/generations/${id}`),
  createGeneration: (payload: Record<string, unknown>) => request<BreezeGeneration>('/api/v2/generations', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
  }),
  cancel: (id: string) => request(`/api/v2/generations/${id}/cancel`, {method: 'POST'}),
  resume: (id: string) => request<BreezeGeneration>(`/api/v2/generations/${id}/resume`, {method: 'POST'}),
  deleteGeneration: (id: string) => request(`/api/v2/generations/${id}`, {method: 'DELETE'}),
  designVoice: (payload: Record<string, unknown>) => request<BreezeVoice>('/api/v2/voices/design', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
  }),
  cloneVoice: (data: FormData) => request<BreezeVoice>('/api/v2/voices/clone', {method: 'POST', body: data}),
  previewVoice: (id: string, payload: Record<string, unknown>) => request<{voice_id: string; text: string; audio_url: string}>(`/api/v2/voices/${id}/preview`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
  }),
  deleteVoice: (id: string) => request(`/api/v2/voices/${id}`, {method: 'DELETE'}),
}
