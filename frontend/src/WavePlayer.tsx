import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'
import TimelinePlugin from 'wavesurfer.js/dist/plugins/timeline.esm.js'
import type { Generation } from './types'

interface Props {
  generation: Generation
  accentColor?: string
}

export default function WavePlayer({generation, accentColor = '#d9ff57'}: Props) {
  const waveform = useRef<HTMLDivElement>(null)
  const script = useRef<HTMLDivElement>(null)
  const wave = useRef<WaveSurfer | null>(null)
  const [playing, setPlaying] = useState(false)
  const [active, setActive] = useState(-1)
  const [speed, setSpeed] = useState(1)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(generation.duration || 0)

  useEffect(() => {
    if (!waveform.current || !generation.audio?.mp3) return
    const regions = RegionsPlugin.create()
    const timeline = TimelinePlugin.create({
      height: 22,
      style: {fontSize: '9px', color: '#77736a'},
    })
    const instance = WaveSurfer.create({
      container: waveform.current,
      url: generation.audio.mp3,
      waveColor: '#8e8a80',
      progressColor: accentColor,
      cursorColor: '#ffffff',
      cursorWidth: 1,
      height: 92,
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
      normalize: true,
      plugins: [regions, timeline],
    })
    wave.current = instance
    instance.on('ready', () => {
      setDuration(instance.getDuration())
      setCurrentTime(instance.getCurrentTime())
      generation.phrases?.forEach((phrase, index) => {
        if (phrase.start_time == null || phrase.end_time == null) return
        regions.addRegion({
          id: String(index), start: phrase.start_time, end: phrase.end_time,
          color: index % 2 ? `${accentColor}0a` : 'rgba(255,255,255,.025)', drag: false, resize: false,
        })
      })
    })
    instance.on('audioprocess', current => {
      const index = generation.phrases?.findIndex(p => p.start_time != null && p.end_time != null && current >= p.start_time && current < p.end_time) ?? -1
      setActive(previous => previous === index ? previous : index)
    })
    instance.on('timeupdate', current => setCurrentTime(current))
    instance.on('play', () => setPlaying(true))
    instance.on('pause', () => setPlaying(false))
    instance.on('finish', () => { setPlaying(false); setCurrentTime(instance.getDuration()) })
    regions.on('region-clicked', region => {
      instance.setTime(region.start)
      instance.play()
    })
    return () => { instance.destroy(); wave.current = null }
  }, [accentColor, generation.id, generation.audio?.mp3, generation.phrases])

  useEffect(() => {
    if (active < 0 || !script.current) return
    script.current.querySelector(`[data-phrase="${active}"]`)?.scrollIntoView({behavior: 'smooth', block: 'center'})
  }, [active])

  const seek = (amount: number) => {
    const instance = wave.current
    if (instance) instance.setTime(Math.max(0, Math.min(instance.getDuration(), instance.getCurrentTime() + amount)))
  }

  const chooseSpeed = (value: number) => {
    setSpeed(value)
    wave.current?.setPlaybackRate(value, true)
  }

  const jumpPhrase = (index: number) => {
    const phrase = generation.phrases?.[index]
    if (phrase?.start_time != null) {
      wave.current?.setTime(phrase.start_time)
      wave.current?.play()
    }
  }

  return <section className="player-card">
    <div className="player-heading">
      <div><span className="eyebrow">NOW SHADOWING</span><h2>{generation.title}</h2></div>
      <div className="download-row">
        {generation.audio?.mp3 && <a className="download-button primary-download" href={generation.audio.mp3} download>
          <span aria-hidden="true">↓</span><span><strong>Download MP3</strong><small>Best for any device</small></span>
        </a>}
        {generation.audio?.wav && <a className="download-button" href={generation.audio.wav} download>
          <span aria-hidden="true">↓</span><span><strong>WAV</strong><small>Lossless audio</small></span>
        </a>}
      </div>
    </div>
    <div ref={waveform} className="waveform" />
    <div className="wave-time-row" aria-live="off"><span>{formatTime(currentTime)}</span><span>{formatTime(duration)}</span></div>
    <div className="transport">
      <button onClick={() => seek(-10)}>−10</button>
      <button className="play" onClick={() => wave.current?.playPause()}>{playing ? 'Pause' : 'Play'}</button>
      <button onClick={() => seek(10)}>+10</button>
      <button onClick={() => active >= 0 && jumpPhrase(active)}>Repeat phrase</button>
      <select value={speed} onChange={event => chooseSpeed(Number(event.target.value))} aria-label="Playback speed">
        {[.75, .85, 1, 1.1, 1.25].map(value => <option key={value} value={value}>{value}×</option>)}
      </select>
    </div>
    <div ref={script} className="sync-script">
      {generation.phrases?.map((phrase, index) => <button
        key={index}
        data-phrase={index}
        className={active === index ? 'phrase active' : 'phrase'}
        onClick={() => jumpPhrase(index)}
      >{phrase.text}</button>)}
    </div>
  </section>
}

function formatTime(value: number) {
  if (!Number.isFinite(value) || value < 0) return '0:00'
  const seconds = Math.floor(value)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}
