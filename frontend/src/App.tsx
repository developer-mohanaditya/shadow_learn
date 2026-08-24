import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import type { Backup, Engine, Generation, Health, Page, Voice } from './types'
import WavePlayer from './WavePlayer'

const nav: {id: Page; label: string; glyph: string}[] = [
  {id: 'studio', label: 'Speech Studio', glyph: '✦'},
  {id: 'voices', label: 'Voice Library', glyph: '◉'},
  {id: 'history', label: 'History', glyph: '↺'},
  {id: 'settings', label: 'Settings', glyph: '⌁'},
]
const voicePreviewText = 'The morning air feels crisp and bright. Take a steady breath, speak clearly, and let every sentence flow naturally.'

export default function App() {
  const [page, setPage] = useState<Page>('studio')
  const [engines, setEngines] = useState<Engine[]>([])
  const [voices, setVoices] = useState<Voice[]>([])
  const [selected, setSelected] = useState<Generation | null>(null)
  const refresh = useCallback(async () => {
    const [engineData, voiceData] = await Promise.all([api.engines(), api.voices()])
    setEngines(engineData); setVoices(voiceData)
  }, [])
  useEffect(() => { refresh().catch(console.error) }, [refresh])

  return <div className="app-shell">
    <aside>
      <div className="brand"><div className="brand-mark">S</div><div><strong>Shadow</strong><span>LEARN</span></div></div>
      <nav>{nav.map(item => <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)}><span>{item.glyph}</span>{item.label}</button>)}</nav>
      <div className="privacy"><span className="status-dot"/>Private on this Mac<small>Nothing leaves your device</small></div>
    </aside>
    <main>
      {page === 'studio' && <Studio engines={engines} voices={voices} selected={selected} onSelected={setSelected} />}
      {page === 'voices' && <Voices voices={voices} engines={engines} refresh={refresh} />}
      {page === 'history' && <History onOpen={async id => {setSelected(await api.generation(id)); setPage('studio')}} />}
      {page === 'settings' && <Settings />}
    </main>
  </div>
}

function Studio({engines, voices, selected, onSelected}: {engines: Engine[]; voices: Voice[]; selected: Generation | null; onSelected: (value: Generation | null) => void}) {
  const [text, setText] = useState('')
  const [engine, setEngine] = useState('')
  const [voice, setVoice] = useState('')
  const [accent, setAccent] = useState<'us'|'uk'>('us')
  const [pace, setPace] = useState(1)
  const [mood, setMood] = useState('neutral')
  const [expressiveness, setExpressiveness] = useState(.5)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const textarea = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!selected?.raw_text) return
    setText(selected.raw_text)
    setEngine(selected.engine)
    setVoice(selected.voice_id || '')
    const saved = selected.settings || {}
    if (saved.accent === 'us' || saved.accent === 'uk') setAccent(saved.accent)
    if (typeof saved.pace === 'number') setPace(saved.pace)
    if (typeof saved.mood === 'string') setMood(saved.mood)
    if (typeof saved.expressiveness === 'number') setExpressiveness(saved.expressiveness)
  }, [selected?.id])

  useEffect(() => {
    if (!engine && !selected?.engine) setEngine(
      engines.find(item => item.id === 'kokoro' && item.available)?.id ||
      engines.find(item => item.available && !item.capabilities.development_only)?.id ||
      engines.find(item => item.available)?.id || ''
    )
  }, [engines, engine, selected?.engine])
  const compatibleVoices = useMemo(() => voices.filter(item => item.engine === engine && item.accent === accent), [voices, engine, accent])
  useEffect(() => {
    const savedVoice = selected?.engine === engine ? selected.voice_id : undefined
    if (savedVoice && compatibleVoices.some(item => item.id === savedVoice)) {
      if (voice !== savedVoice) setVoice(savedVoice)
    } else if (!compatibleVoices.some(item => item.id === voice)) {
      setVoice(compatibleVoices[0]?.id || '')
    }
  }, [compatibleVoices, engine, selected?.engine, selected?.voice_id, voice])

  const generate = async () => {
    setBusy(true); setError(''); onSelected(null)
    try {
      const generation = await api.createGeneration({text, engine, voice_id: voice || null, accent, pace, mood, expressiveness})
      onSelected(generation)
      const source = new EventSource(`/api/generations/${generation.id}/events`)
      source.onmessage = event => {
        const update = JSON.parse(event.data) as Generation
        onSelected(update)
        if (['complete', 'failed', 'cancelled'].includes(update.status)) { source.close(); setBusy(false) }
      }
      source.onerror = () => { source.close(); setBusy(false) }
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); setBusy(false) }
  }
  const insertCue = (value: string) => {
    const node = textarea.current
    if (!node) return
    const start = node.selectionStart, end = node.selectionEnd
    const content = value === 'emphasis' ? `[emphasis]${text.slice(start, end) || 'important words'}[/emphasis]` : `[pause:${value}]`
    setText(text.slice(0, start) + content + text.slice(end))
  }
  const uploadText = async (file?: File) => {
    if (!file) return
    if (!/\.(txt|md)$/i.test(file.name)) { setError('Please choose a .txt or .md file'); return }
    setText((await file.text()).slice(0, 25000))
  }

  return <div className="page studio-page">
    <header><div><span className="eyebrow">CREATE</span><h1>Speech Studio</h1><p>Turn any script into a voice worth shadowing.</p></div><span className="local-pill">● LOCAL INFERENCE</span></header>
    <section className="composer">
      <div className="composer-toolbar">
        <div className="cue-buttons"><button onClick={() => insertCue('short')}>+ Short pause</button><button onClick={() => insertCue('medium')}>+ Medium pause</button><button onClick={() => insertCue('emphasis')}>+ Emphasis</button></div>
        <label className="file-button">Upload .txt / .md<input type="file" accept=".txt,.md,text/plain,text/markdown" onChange={event => uploadText(event.target.files?.[0])}/></label>
      </div>
      <textarea ref={textarea} value={text} maxLength={25000} onChange={event => setText(event.target.value)} placeholder="Paste a speech, dialogue, article, or practice script here…" />
      <div className="character-count">{text.length.toLocaleString()} / 25,000 characters</div>
      <div className="controls-grid">
        <label>Engine<select value={engine} onChange={event => setEngine(event.target.value)}>{engines.map(item => <option key={item.id} value={item.id} disabled={!item.available}>{item.name}{!item.available ? ' — not installed' : ''}</option>)}</select></label>
        <label>Accent<select value={accent} onChange={event => setAccent(event.target.value as 'us'|'uk')}><option value="us">General American</option><option value="uk">Standard British</option></select></label>
        <label>Voice<select value={voice} onChange={event => setVoice(event.target.value)}><option value="">Engine default</option>{compatibleVoices.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
        <label>Mood<select value={mood} onChange={event => setMood(event.target.value)}>{['neutral','friendly','formal','cheerful','serious','dramatic'].map(value => <option key={value} value={value}>{value[0].toUpperCase()+value.slice(1)}</option>)}</select></label>
        <label>Pace <output>{pace.toFixed(2)}×</output><input type="range" min=".75" max="1.25" step=".05" value={pace} onChange={event => setPace(Number(event.target.value))}/></label>
        <label>Expression <output>{expressiveness.toFixed(1)}</output><input type="range" min="0" max="1.5" step=".1" value={expressiveness} onChange={event => setExpressiveness(Number(event.target.value))}/></label>
      </div>
      {error && <div className="error-banner">{error}</div>}
      <div className="generate-row"><small>{engines.find(item => item.id === engine)?.reason}</small><button className="primary" disabled={!text.trim() || !engine || busy} onClick={generate}>{busy ? `Generating ${Math.round((selected?.progress || 0)*100)}%` : 'Generate speech →'}</button></div>
    </section>
    {selected && selected.status !== 'complete' && <JobStatus generation={selected} />}
    {selected?.status === 'complete' && <WavePlayer generation={selected} />}
  </div>
}

function JobStatus({generation}: {generation: Generation}) {
  return <section className={`job-card ${generation.status}`}><div><strong>{generation.status === 'failed' ? 'Generation failed' : 'Building your practice audio'}</strong><span>{generation.error || `${Math.round(generation.progress * 100)}% complete`}</span></div><div className="progress"><i style={{width: `${generation.progress*100}%`}}/></div></section>
}

function Voices({voices, engines, refresh}: {voices: Voice[]; engines: Engine[]; refresh: () => Promise<void>}) {
  const [name, setName] = useState('My voice')
  const [engine, setEngine] = useState('chatterbox')
  const [accent, setAccent] = useState('us')
  const [file, setFile] = useState<File | null>(null)
  const [consented, setConsented] = useState(false)
  const [message, setMessage] = useState('')
  const [recording, setRecording] = useState(false)
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const previewAudio = useRef<HTMLAudioElement | null>(null)
  const previewVoice = useRef<string | null>(null)
  const previewUrls = useRef(new Map<string, string>())
  const [loadingPreview, setLoadingPreview] = useState<string | null>(null)
  const [playingPreview, setPlayingPreview] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState('')
  useEffect(() => {
    const choices = engines.filter(item => item.available && item.capabilities.voice_cloning)
    if (choices.length && !choices.some(item => item.id === engine)) setEngine(choices[0].id)
  }, [engines, engine])
  useEffect(() => () => { previewAudio.current?.pause() }, [])
  const togglePreview = async (item: Voice) => {
    setPreviewError('')
    if (previewVoice.current === item.id && previewAudio.current) {
      if (previewAudio.current.paused) {
        await previewAudio.current.play()
        setPlayingPreview(item.id)
      } else {
        previewAudio.current.pause()
        setPlayingPreview(null)
      }
      return
    }
    previewAudio.current?.pause()
    setPlayingPreview(null)
    setLoadingPreview(item.id)
    try {
      let url = previewUrls.current.get(item.id)
      if (!url) {
        const preview = await api.voicePreview(item.id)
        url = preview.audio_url
        previewUrls.current.set(item.id, url)
      }
      const audio = new Audio(url)
      previewAudio.current = audio
      previewVoice.current = item.id
      audio.onended = () => setPlayingPreview(null)
      audio.onerror = () => { setPlayingPreview(null); setPreviewError(`Could not play ${item.name}.`) }
      await audio.play()
      setPlayingPreview(item.id)
    } catch (cause) {
      setPreviewError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setLoadingPreview(null)
    }
  }
  const startRecording = async () => {
    if (recording) { recorder.current?.stop(); return }
    const stream = await navigator.mediaDevices.getUserMedia({audio: true})
    chunks.current = []
    const current = new MediaRecorder(stream)
    recorder.current = current
    current.ondataavailable = event => chunks.current.push(event.data)
    current.onstop = () => { setFile(new File(chunks.current, 'recording.m4a', {type: current.mimeType})); stream.getTracks().forEach(track => track.stop()); setRecording(false) }
    current.start(); setRecording(true)
  }
  const save = async () => {
    if (!file) return
    const data = new FormData(); data.set('name', name); data.set('engine', engine); data.set('accent', accent); data.set('consented', String(consented)); data.set('audio', file)
    try { await api.createVoice(data); setMessage('Voice profile saved.'); setFile(null); await refresh() } catch (cause) { setMessage(cause instanceof Error ? cause.message : String(cause)) }
  }
  return <div className="page"><header><div><span className="eyebrow">YOUR SOUND</span><h1>Voice Library</h1><p>Preset voices and private, reusable clones.</p></div></header>
    <div className="two-column">
      <section className="panel"><h2>Create a voice clone</h2><p className="muted">Use 10–30 seconds of clean speech with one speaker and little background noise.</p>
        <label>Name<input value={name} onChange={event => setName(event.target.value)}/></label>
        <div className="form-row"><label>Engine<select value={engine} onChange={event => setEngine(event.target.value)}>{engines.filter(item => item.capabilities.voice_cloning).map(item => <option key={item.id} value={item.id} disabled={!item.available}>{item.name}{!item.available ? ' — not installed' : ''}</option>)}</select></label><label>Accent<select value={accent} onChange={event => setAccent(event.target.value)}><option value="us">US</option><option value="uk">UK</option></select></label></div>
        <div className="record-row"><button className={recording ? 'record active' : 'record'} onClick={startRecording}>{recording ? '■ Stop recording' : '● Record in browser'}</button><span>or</span><label className="file-button">Choose audio<input type="file" accept=".wav,.mp3,.m4a,audio/*" onChange={event => setFile(event.target.files?.[0] || null)}/></label></div>
        {file && <div className="file-chip">{file.name}</div>}
        <label className="checkbox"><input type="checkbox" checked={consented} onChange={event => setConsented(event.target.checked)}/>I own this voice or have explicit permission to use it.</label>
        <button className="primary" disabled={!file || !consented} onClick={save}>Save voice profile</button>{message && <p className="message">{message}</p>}
      </section>
      <section className="panel voice-library-panel"><h2>Available voices</h2><p className="preview-script"><span>PREVIEW SCRIPT</span>“{voicePreviewText}”</p>{previewError && <div className="preview-error">{previewError}</div>}<div className="voice-list">{voices.map(item => <div className={playingPreview === item.id ? 'voice-item playing' : 'voice-item'} key={item.id}><button className="voice-preview" aria-label={`${playingPreview === item.id ? 'Pause' : 'Play'} preview for ${item.name}`} disabled={loadingPreview !== null && loadingPreview !== item.id} onClick={() => togglePreview(item)}><span>{loadingPreview === item.id ? '···' : playingPreview === item.id ? 'Ⅱ' : '▶'}</span></button><div className="avatar">{item.name[0]}</div><div className="voice-identity"><strong>{item.name}</strong><span>{item.accent.toUpperCase()} · {item.engine} · {item.kind}</span></div>{item.kind === 'cloned' && <button className="voice-delete" onClick={async () => {await api.deleteVoice(item.id); await refresh()}}>Delete</button>}</div>)}</div></section>
    </div>
  </div>
}

function History({onOpen}: {onOpen: (id: string) => void}) {
  const [items, setItems] = useState<Generation[]>([])
  const [query, setQuery] = useState('')
  const load = useCallback(() => api.generations(query).then(result => setItems(result.items)), [query])
  useEffect(() => { load().catch(console.error) }, [load])
  return <div className="page"><header><div><span className="eyebrow">ARCHIVE</span><h1>History</h1><p>Every script and finished practice recording.</p></div><input className="search" placeholder="Search scripts…" value={query} onChange={event => setQuery(event.target.value)}/></header>
    <section className="history-list">{items.length === 0 && <div className="empty">No generations yet.</div>}{items.map(item => <article key={item.id}><div className={`state ${item.status}`}/><div className="history-main"><strong>{item.title}</strong><span>{new Date(item.created_at).toLocaleString()} · {item.engine} {item.duration ? `· ${item.duration < 60 ? `${Math.round(item.duration)} sec` : `${Math.round(item.duration/60)} min`}` : ''}</span>{item.error && <small>{item.error}</small>}</div><div className="history-actions">{item.status === 'complete' && <button onClick={() => onOpen(item.id)}>Open</button>}{['failed','interrupted','cancelled'].includes(item.status) && <button onClick={async () => {await api.resume(item.id); await load()}}>Resume</button>}<button className="danger" onClick={async () => {if(confirm('Delete this generation and its audio?')) {await api.deleteGeneration(item.id); await load()}}}>Delete</button></div></article>)}</section>
  </div>
}

function Settings() {
  const [health, setHealth] = useState<Health | null>(null)
  const [backups, setBackups] = useState<Backup[]>([])
  const load = useCallback(async () => {setHealth(await api.health()); setBackups(await api.backups())}, [])
  useEffect(() => {load().catch(console.error)}, [load])
  return <div className="page"><header><div><span className="eyebrow">SYSTEM</span><h1>Settings</h1><p>Persistence, engines, storage, and recovery.</p></div></header>
    <div className="settings-grid">
      <section className="panel"><h2>System health</h2><dl><div><dt>Database</dt><dd className="healthy">● {health?.database || 'Checking…'}</dd></div><div><dt>Data directory</dt><dd className="path">{health?.data_directory}</dd></div><div><dt>Free space</dt><dd>{health ? formatBytes(health.disk_free) : '—'}</dd></div><div><dt>Latest backup</dt><dd>{health?.last_backup ? new Date(health.last_backup.created_at).toLocaleString() : 'None yet'}</dd></div></dl></section>
      <section className="panel"><h2>Inference engines</h2><div className="engine-list">{health?.engines.map(item => <div key={item.id}><span className={item.available ? 'engine-dot online' : 'engine-dot'}/><div><strong>{item.name}</strong><small>{item.available ? 'Ready' : item.reason}</small></div></div>)}</div></section>
      <section className="panel wide"><div className="panel-heading"><div><h2>Local backups</h2><p className="muted">Seven daily and four weekly database snapshots are retained.</p></div><button className="primary" onClick={async () => {await api.createBackup(); await load()}}>Create backup</button></div><div className="backup-list">{backups.map(item => <div key={item.id}><span>{new Date(item.created_at).toLocaleString()} · {item.kind} · {formatBytes(item.size_bytes)}</span><button onClick={async () => {if(confirm('Restore this backup? The service must be restarted afterwards.')) await api.restoreBackup(item.id)}}>Restore</button></div>)}</div></section>
    </div>
  </div>
}

function formatBytes(value: number) {
  if (!value) return '0 B'
  const unit = Math.floor(Math.log(value) / Math.log(1024))
  return `${(value / 1024 ** unit).toFixed(1)} ${['B','KB','MB','GB','TB'][unit]}`
}
