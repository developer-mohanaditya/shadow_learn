import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'
import type { Generation } from './types'

interface Props {
  generation: Generation
}

export default function WavePlayer({generation}: Props) {
  const waveform = useRef<HTMLDivElement>(null)
  const script = useRef<HTMLDivElement>(null)
  const wave = useRef<WaveSurfer | null>(null)
  const [playing, setPlaying] = useState(false)
  const [active, setActive] = useState(-1)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    if (!waveform.current || !generation.audio?.mp3) return
    const regions = RegionsPlugin.create()
    const instance = WaveSurfer.create({
      container: waveform.current,
      url: generation.audio.mp3,
      waveColor: '#8e8a80',
      progressColor: '#d9ff57',
      cursorColor: '#ffffff',
      cursorWidth: 1,
      height: 92,
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
      normalize: true,
      plugins: [regions],
    })
    wave.current = instance
    instance.on('ready', () => {
      generation.phrases?.forEach((phrase, index) => {
        if (phrase.start_time == null || phrase.end_time == null) return
        regions.addRegion({
          id: String(index), start: phrase.start_time, end: phrase.end_time,
          color: index % 2 ? 'rgba(217,255,87,.025)' : 'rgba(255,255,255,.025)', drag: false, resize: false,
        })
      })
    })
    instance.on('audioprocess', current => {
      const index = generation.phrases?.findIndex(p => p.start_time != null && p.end_time != null && current >= p.start_time && current < p.end_time) ?? -1
      setActive(previous => previous === index ? previous : index)
    })
    instance.on('play', () => setPlaying(true))
    instance.on('pause', () => setPlaying(false))
    instance.on('finish', () => setPlaying(false))
    regions.on('region-clicked', region => {
      instance.setTime(region.start)
      instance.play()
    })
    return () => { instance.destroy(); wave.current = null }
  }, [generation.id, generation.audio?.mp3, generation.phrases])

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
        <a className="small-button" href={generation.audio.wav} download>WAV</a>
        <a className="small-button" href={generation.audio.mp3} download>MP3</a>
      </div>
    </div>
    <div ref={waveform} className="waveform" />
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

