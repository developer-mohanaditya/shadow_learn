import {useCallback, useEffect, useMemo, useRef, useState} from 'react'
import {breezeApi} from './api'
import type {BreezeCapabilities, BreezeGeneration, BreezePage, BreezeVoice} from './types'
import WavePlayer from './WavePlayer'
import VersionSwitch from './VersionSwitch'

const nav: {id: BreezePage; label: string; glyph: string}[] = [
  {id: 'studio', label: 'Breeze Studio', glyph: '✦'},
  {id: 'lab', label: 'Voice Lab', glyph: '◌'},
  {id: 'voices', label: 'Voice Library', glyph: '◉'},
  {id: 'history', label: 'History', glyph: '↺'},
  {id: 'settings', label: 'Settings', glyph: '⌁'},
]
const previewText = 'Every clear sentence begins with a steady breath. Let the words move naturally, with confidence and warmth.'

export default function BreezeApp({onVersionChange}: {onVersionChange: (version: 'v1' | 'v2') => void}) {
  const [page, setPage] = useState<BreezePage>('studio')
  const [voices, setVoices] = useState<BreezeVoice[]>([])
  const [capabilities, setCapabilities] = useState<BreezeCapabilities | null>(null)
  const [selected, setSelected] = useState<BreezeGeneration | null>(null)
  const refresh = useCallback(async () => {
    const [voiceData, capabilityData] = await Promise.all([breezeApi.voices(), breezeApi.capabilities()])
    setVoices(voiceData); setCapabilities(capabilityData)
  }, [])
  useEffect(() => {refresh().catch(console.error)}, [refresh])
  return <div className="app-shell breeze-shell">
    <aside>
      <div className="brand-wrap"><div className="brand"><div className="brand-mark">B</div><div><strong>Shadow</strong><span>BREEZE V2</span></div></div><VersionSwitch version="v2" onChange={onVersionChange}/></div>
      <nav>{nav.map(item => <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => setPage(item.id)}><span>{item.glyph}</span>{item.label}</button>)}</nav>
      <div className="privacy"><span className="status-dot"/>Private MLX inference<small>Runs on this Mac</small></div>
    </aside>
    <main>
      {page === 'studio' && <BreezeStudio voices={voices} capabilities={capabilities} selected={selected} onSelected={setSelected}/>} 
      {page === 'lab' && <VoiceLab refresh={refresh}/>} 
      {page === 'voices' && <VoiceLibrary voices={voices} refresh={refresh}/>} 
      {page === 'history' && <BreezeHistory onOpen={async id => {setSelected(await breezeApi.generation(id)); setPage('studio')}}/>}
      {page === 'settings' && <BreezeSettings capabilities={capabilities}/>} 
    </main>
  </div>
}

function BreezeStudio({voices, capabilities, selected, onSelected}: {voices: BreezeVoice[]; capabilities: BreezeCapabilities | null; selected: BreezeGeneration | null; onSelected: (value: BreezeGeneration | null) => void}) {
  const [text, setText] = useState('')
  const [mode, setMode] = useState<'design' | 'clone' | 'direction'>('design')
  const [language, setLanguage] = useState<'en' | 'zh'>('en')
  const [accent, setAccent] = useState('General American English')
  const [voiceId, setVoiceId] = useState('')
  const [description, setDescription] = useState('A warm, confident adult male voice with a natural conversational quality.')
  const [direction, setDirection] = useState('Speak clearly and naturally at a measured pace, with thoughtful pauses and expressive emphasis.')
  const [seed, setSeed] = useState(42)
  const [cfg, setCfg] = useState(4)
  const [temperature, setTemperature] = useState(.9)
  const [advanced, setAdvanced] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [previewing, setPreviewing] = useState(false)
  const preview = useRef<HTMLAudioElement | null>(null)
  const compatible = useMemo(() => voices.filter(v =>
    v.language === language &&
    (mode === 'design' ? v.kind === 'designed' && v.accent_direction === accent : v.kind === 'cloned')
  ), [accent, voices, language, mode])
  useEffect(() => {if (!compatible.some(v => v.id === voiceId)) setVoiceId(compatible[0]?.id || '')}, [compatible, voiceId])
  useEffect(() => {
    const selectedVoice = compatible.find(v => v.id === voiceId)
    if (mode === 'design' && selectedVoice) {
      setSeed(selectedVoice.seed)
      setCfg(selectedVoice.cfg_scale)
    }
  }, [compatible, mode, voiceId])
  useEffect(() => {
    if (!selected?.raw_text) return
    setText(selected.raw_text); setMode(selected.mode); setLanguage(selected.language); setAccent(selected.accent_direction || accent)
    setVoiceId(selected.voice_id || ''); setDirection(selected.direction || direction)
  }, [selected?.id])
  useEffect(() => () => preview.current?.pause(), [])
  const create = async () => {
    setBusy(true); setError(''); onSelected(null)
    try {
      const generation = await breezeApi.createGeneration({text, mode, language, accent_direction: accent, voice_id: voiceId || null, voice_description: description, direction, seed, cfg_scale: mode === 'clone' ? 1 : cfg, temperature})
      onSelected(generation)
      const source = new EventSource(`/api/v2/generations/${generation.id}/events`)
      source.onmessage = event => {
        const update = JSON.parse(event.data) as BreezeGeneration
        onSelected(update)
        if (['complete', 'failed', 'cancelled'].includes(update.status)) {source.close(); setBusy(false)}
      }
      source.onerror = () => {source.close(); setBusy(false)}
    } catch (cause) {setError(messageOf(cause)); setBusy(false)}
  }
  const playPreview = async () => {
    if (!voiceId) return
    if (preview.current && !preview.current.paused) {preview.current.pause(); setPreviewing(false); return}
    setError('')
    try {
      const result = await breezeApi.previewVoice(voiceId, {text: previewText, direction, seed})
      preview.current?.pause()
      const player = new Audio(`${result.audio_url}?v=${Date.now()}`); preview.current = player
      player.onended = () => setPreviewing(false)
      await player.play(); setPreviewing(true)
    } catch (cause) {setError(messageOf(cause))}
  }
  const addEvent = (event: string) => setDirection(value => `${value.trim()} ${event}`)
  const uploadText = async (file?: File) => {if (file) setText((await file.text()).slice(0, 25000))}
  const needsClone = mode !== 'design'
  return <div className="page studio-page">
    <header><div><span className="eyebrow">BREEZE TTS 2 · MLX</span><h1>Breeze Studio</h1><p>Design, clone, and direct expressive voices in English or Chinese.</p></div><span className="local-pill">● LOCAL APPLE SILICON</span></header>
    {!capabilities?.available && <div className="error-banner capability-warning">Breeze is not ready: {capabilities?.reason || 'checking the local model…'}</div>}
    <section className="mode-tabs">{(['design','clone','direction'] as const).map(value => <button key={value} className={mode === value ? 'active' : ''} onClick={() => setMode(value)}><strong>{value === 'design' ? 'Voice Design' : value === 'clone' ? 'Instant Clone' : 'Directed Clone'}</strong><small>{value === 'design' ? 'Create a voice from words' : value === 'clone' ? 'Copy a saved reference' : 'Act with a cloned voice'}</small></button>)}</section>
    <section className="composer breeze-composer">
      <div className="composer-toolbar"><div className="cue-buttons"><button onClick={() => addEvent('[laughs softly]')}>+ Laugh</button><button onClick={() => addEvent('[whispers briefly]')}>+ Whisper</button><button onClick={() => addEvent('[sighs, then continues]')}>+ Sigh</button><button onClick={() => addEvent('[takes a thoughtful pause]')}>+ Pause</button></div><label className="file-button">Upload .txt / .md<input type="file" accept=".txt,.md,text/plain,text/markdown" onChange={event => uploadText(event.target.files?.[0])}/></label></div>
      <textarea value={text} maxLength={25000} onChange={event => setText(event.target.value)} placeholder="Write or paste the script you want Breeze to perform…"/>
      <div className="character-count">{text.length.toLocaleString()} / 25,000 characters</div>
      <div className="breeze-controls">
        <label>Language<select value={language} onChange={event => setLanguage(event.target.value as 'en' | 'zh')}><option value="en">English</option><option value="zh">Chinese</option></select></label>
        {language === 'en' && <label>Accent direction<select value={accent} onChange={event => setAccent(event.target.value)}>{(capabilities?.english_directions || ['General American English','Indian English','British English','Neutral international English']).map(value => <option key={value}>{value}</option>)}</select></label>}
        <label>Saved voice<div className="studio-voice-select"><select value={voiceId} onChange={event => setVoiceId(event.target.value)}><option value="">{mode === 'design' ? 'Custom voice description…' : 'Choose a cloned voice'}</option>{compatible.map(v => <option value={v.id} key={v.id}>{v.name} — {v.accent_direction || 'Custom voice'}</option>)}</select><button type="button" className={previewing ? 'studio-voice-preview playing' : 'studio-voice-preview'} disabled={!voiceId} onClick={playPreview}>{previewing ? 'Ⅱ' : '▶'}</button></div></label>
      </div>
      {mode === 'design' && !voiceId && <label className="prompt-field">Voice description<textarea value={description} onChange={event => setDescription(event.target.value)} placeholder="Age, timbre, energy, gender presentation, vocal texture…"/></label>}
      <label className="prompt-field">Performance direction<textarea value={direction} onChange={event => setDirection(event.target.value)} placeholder="Describe emotion, pace, delivery, pauses, and vocal events…"/></label>
      <div className="advanced-toggle"><button onClick={() => setAdvanced(!advanced)}>{advanced ? 'Hide' : 'Show'} advanced controls</button><span>Model: Vireo 3B MLX mixed 4-bit</span></div>
      {advanced && <div className="advanced-grid"><label>Seed<input type="number" min="0" value={seed} onChange={e => setSeed(Number(e.target.value))}/></label><label>Guidance <output>{mode === 'clone' ? '1.0' : cfg.toFixed(1)}</output><input disabled={mode === 'clone'} type="range" min=".5" max="8" step=".5" value={mode === 'clone' ? 1 : cfg} onChange={e => setCfg(Number(e.target.value))}/></label><label>Variation <output>{temperature.toFixed(1)}</output><input type="range" min=".2" max="1.5" step=".1" value={temperature} onChange={e => setTemperature(Number(e.target.value))}/></label></div>}
      {needsClone && compatible.length === 0 && <div className="info-banner">Create a cloned voice in Voice Lab before using this mode.</div>}
      {error && <div className="error-banner">{error}</div>}
      <div className="generate-row"><small>Phrase timing, waveform playback, highlighting, WAV and MP3 are created automatically.</small><button className="primary" disabled={!text.trim() || busy || !capabilities?.available || (needsClone && !voiceId)} onClick={create}>{busy ? `Generating ${Math.round((selected?.progress || 0) * 100)}%` : 'Generate with Breeze →'}</button></div>
    </section>
    {selected && selected.status !== 'complete' && <JobCard generation={selected}/>} 
    {selected?.status === 'complete' && <><div className="metrics"><span>Audio <strong>{formatTime(selected.duration || 0)}</strong></span><span>Generated in <strong>{formatTime(selected.generation_seconds || 0)}</strong></span><span>Real-time factor <strong>{selected.real_time_factor?.toFixed(2) || '—'}</strong></span></div><WavePlayer generation={selected} accentColor="#4da3ff"/></>}
  </div>
}

function VoiceLab({refresh}: {refresh: () => Promise<void>}) {
  const [kind, setKind] = useState<'design' | 'clone'>('design')
  const [name, setName] = useState('My Breeze voice')
  const [language, setLanguage] = useState<'en' | 'zh'>('en')
  const [accent, setAccent] = useState('Indian English')
  const [description, setDescription] = useState('A clear, confident adult male voice with a warm tone and measured delivery.')
  const [transcript, setTranscript] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [consented, setConsented] = useState(false)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async () => {
    setBusy(true); setMessage('')
    try {
      if (kind === 'design') await breezeApi.designVoice({name, language, accent_direction: accent, description, seed: 42, cfg_scale: 4})
      else {
        if (!file) throw new Error('Choose a reference recording.')
        const data = new FormData(); data.set('name', name); data.set('language', language); data.set('accent_direction', accent); data.set('reference_text', transcript); data.set('consented', String(consented)); data.set('audio', file)
        await breezeApi.cloneVoice(data)
      }
      await refresh(); setMessage(`${kind === 'design' ? 'Designed' : 'Cloned'} voice saved to your local library.`)
    } catch (cause) {setMessage(messageOf(cause))} finally {setBusy(false)}
  }
  return <div className="page"><header><div><span className="eyebrow">CREATE A REUSABLE VOICE</span><h1>Voice Lab</h1><p>Describe a voice or clone one from a private reference recording.</p></div></header>
    <section className="panel voice-lab"><div className="segmented"><button className={kind === 'design' ? 'active' : ''} onClick={() => setKind('design')}>Design from description</button><button className={kind === 'clone' ? 'active' : ''} onClick={() => setKind('clone')}>Clone from audio</button></div>
      <div className="form-row"><label>Voice name<input value={name} onChange={e => setName(e.target.value)}/></label><label>Language<select value={language} onChange={e => setLanguage(e.target.value as 'en' | 'zh')}><option value="en">English</option><option value="zh">Chinese</option></select></label></div>
      <label>Accent or speaking style<input value={accent} onChange={e => setAccent(e.target.value)} placeholder="Any natural-language accent direction"/></label>
      {kind === 'design' ? <label>Voice description<textarea className="compact-textarea" value={description} onChange={e => setDescription(e.target.value)}/></label> : <>
        <p className="muted">Use 3–60 seconds of clean, single-speaker audio. The transcript must match every spoken word exactly.</p>
        <label className="file-button large">Choose WAV, MP3, or M4A<input type="file" accept=".wav,.mp3,.m4a,audio/*" onChange={e => setFile(e.target.files?.[0] || null)}/></label>{file && <div className="file-chip">{file.name}</div>}
        <label>Exact reference transcript<textarea className="compact-textarea" value={transcript} onChange={e => setTranscript(e.target.value)} placeholder="Type exactly what is spoken in the recording…"/></label>
        <label className="checkbox"><input type="checkbox" checked={consented} onChange={e => setConsented(e.target.checked)}/>I own this voice or have explicit permission to use it.</label>
      </>}
      <button className="primary" disabled={busy || !name.trim() || (kind === 'design' ? description.trim().length < 10 : !file || !transcript.trim() || !consented)} onClick={save}>{busy ? 'Saving…' : 'Save to Voice Library'}</button>{message && <p className="message">{message}</p>}
    </section>
  </div>
}

function VoiceLibrary({voices, refresh}: {voices: BreezeVoice[]; refresh: () => Promise<void>}) {
  const audio = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState('')
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')
  useEffect(() => () => audio.current?.pause(), [])
  const preview = async (voice: BreezeVoice) => {
    if (playing === voice.id && audio.current) {audio.current.pause(); setPlaying(''); return}
    setLoading(voice.id); setError('')
    try {
      const result = await breezeApi.previewVoice(voice.id, {text: previewText, direction: 'Speak clearly, warmly, and naturally.'})
      audio.current?.pause(); const player = new Audio(`${result.audio_url}?v=${Date.now()}`); audio.current = player
      player.onended = () => setPlaying(''); await player.play(); setPlaying(voice.id)
    } catch (cause) {setError(messageOf(cause))} finally {setLoading('')}
  }
  return <div className="page"><header><div><span className="eyebrow">YOUR BREEZE VOICES</span><h1>Voice Library</h1><p>Reusable designed and cloned voices, stored only on this Mac.</p></div></header>
    <section className="panel voice-library-panel"><p className="preview-script"><span>PREVIEW SCRIPT</span>“{previewText}”</p>{error && <div className="error-banner">{error}</div>}<div className="breeze-voice-grid">{voices.map(voice => <article key={voice.id} className={playing === voice.id ? 'playing' : ''}><div className="avatar">{voice.name[0]}</div><div><strong>{voice.name}</strong><span>{voice.kind} · {voice.language === 'en' ? 'English' : 'Chinese'}</span><small>{voice.accent_direction || voice.description}</small></div><button className="voice-preview" onClick={() => preview(voice)}>{loading === voice.id ? '···' : playing === voice.id ? 'Ⅱ' : '▶'}</button><button className="voice-delete" onClick={async () => {if (confirm(`Delete ${voice.name}?`)) {await breezeApi.deleteVoice(voice.id); await refresh()}}}>Delete</button></article>)}{!voices.length && <div className="empty">No Breeze voices yet. Create one in Voice Lab.</div>}</div></section>
  </div>
}

function BreezeHistory({onOpen}: {onOpen: (id: string) => void}) {
  const [items, setItems] = useState<BreezeGeneration[]>([]); const [query, setQuery] = useState(''); const [playing, setPlaying] = useState('')
  const player = useRef<HTMLAudioElement | null>(null)
  const load = useCallback(() => breezeApi.generations(query).then(data => setItems(data.items)), [query])
  useEffect(() => {load().catch(console.error)}, [load]); useEffect(() => () => player.current?.pause(), [])
  const play = async (item: BreezeGeneration) => {if (playing === item.id && player.current) {player.current.pause(); setPlaying(''); return} player.current?.pause(); const audio = new Audio(item.audio.mp3); player.current = audio; audio.onended = () => setPlaying(''); await audio.play(); setPlaying(item.id)}
  return <div className="page"><header><div><span className="eyebrow">BREEZE ARCHIVE</span><h1>History</h1><p>Scripts, settings, performance metrics, and finished audio.</p></div><input className="search" placeholder="Search…" value={query} onChange={e => setQuery(e.target.value)}/></header><section className="history-list">{items.map(item => <article key={item.id}><div className={`state ${item.status}`}/><div className="history-main"><strong>{item.title}</strong><span>{new Date(item.created_at).toLocaleString()} · {item.mode} · {item.language.toUpperCase()} {item.duration ? `· ${formatTime(item.duration)}` : ''}</span>{item.real_time_factor != null && <small>{item.real_time_factor.toFixed(2)} real-time factor</small>}</div><div className="history-actions">{item.status === 'complete' && <button onClick={() => play(item)}>{playing === item.id ? 'Pause' : '▶ Play'}</button>}{item.audio?.mp3 && <a className="history-download" href={item.audio.mp3} download>↓ MP3</a>}{item.status === 'complete' && <button onClick={() => onOpen(item.id)}>Open</button>}{['failed','interrupted','cancelled'].includes(item.status) && <button onClick={async () => {await breezeApi.resume(item.id); await load()}}>Resume</button>}<button className="danger" onClick={async () => {if (confirm('Delete this generation and its audio?')) {await breezeApi.deleteGeneration(item.id); await load()}}}>Delete</button></div></article>)}{!items.length && <div className="empty">No Breeze generations yet.</div>}</section></div>
}

function BreezeSettings({capabilities}: {capabilities: BreezeCapabilities | null}) {
  return <div className="page"><header><div><span className="eyebrow">BREEZE SYSTEM</span><h1>Settings</h1><p>Local model status and supported capabilities.</p></div></header><div className="settings-grid"><section className="panel"><h2>Inference</h2><dl><div><dt>Status</dt><dd className={capabilities?.available ? 'healthy' : ''}>● {capabilities?.available ? 'Ready locally' : 'Unavailable'}</dd></div><div><dt>Runtime</dt><dd>MLX on Apple Silicon</dd></div><div><dt>Model</dt><dd>Vireo TTS 3B mixed 4-bit</dd></div><div><dt>Network API</dt><dd>None</dd></div></dl>{capabilities?.reason && <p className="muted">{capabilities.reason}</p>}</section><section className="panel"><h2>Capabilities</h2><div className="capability-chips">{['Voice design','Instant cloning','Directed speech','Vocal events','English','Chinese','Phrase highlighting','WAV + MP3'].map(item => <span key={item}>{item}</span>)}</div></section></div></div>
}

function JobCard({generation}: {generation: BreezeGeneration}) {return <section className={`job-card ${generation.status}`}><div><strong>{generation.status === 'failed' ? 'Breeze generation failed' : 'Breeze is performing your script'}</strong><span>{generation.error || `${Math.round(generation.progress * 100)}% complete`}</span></div><div className="progress"><i style={{width: `${generation.progress * 100}%`}}/></div></section>}
function messageOf(value: unknown) {return value instanceof Error ? value.message : String(value)}
function formatTime(value: number) {const seconds = Math.max(0, Math.floor(value || 0)); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`}
