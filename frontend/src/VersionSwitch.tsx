export default function VersionSwitch({version, onChange}: {version: 'v1' | 'v2'; onChange: (version: 'v1' | 'v2') => void}) {
  return <div className="version-switch" aria-label="Choose ShadowLearn version">
    <button className={version === 'v1' ? 'selected' : ''} onClick={() => onChange('v1')}>V1 Classic</button>
    <button className={version === 'v2' ? 'selected' : ''} onClick={() => onChange('v2')}>V2 Breeze</button>
  </div>
}
