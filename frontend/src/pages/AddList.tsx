import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { VoiceRecorder } from '../components/VoiceRecorder'
import { parseList } from '../lib/api'

type Tab = 'type' | 'upload' | 'voice' | 'photo'

const TABS: { id: Tab; label: string }[] = [
  { id: 'type', label: 'Type' },
  { id: 'upload', label: 'Upload file' },
  { id: 'voice', label: 'Record voice' },
  { id: 'photo', label: 'Take photo' },
]

const PLACEHOLDER = `thakkali 1 kg
atta 5 kg
paal 2 litre
toor dal
Golden Harvest rice 10kg
eggs 1 dozen`

export function AddList() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('type')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [audio, setAudio] = useState<Blob | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ready = (tab === 'type' && text.trim()) || ((tab === 'upload' || tab === 'photo') && file) || (tab === 'voice' && audio)

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const result =
        tab === 'type'
          ? await parseList({ text })
          : tab === 'voice'
            ? await parseList({ file: audio!, filename: `voice.${audio!.type.includes('ogg') ? 'ogg' : audio!.type.includes('mp4') ? 'm4a' : 'webm'}` })
            : await parseList({ file: file!, filename: file!.name })
      navigate(`/lists/${result.list_id}`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const switchTab = (next: Tab) => {
    setTab(next)
    setFile(null)
    setError(null)
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="text-2xl font-semibold">Add your list</h1>
      <p className="mt-1 text-stone-600">English, Tamil, Hindi or a mix. Typed, written, spoken or a document.</p>

      <div role="tablist" className="mt-6 grid grid-cols-4 gap-1 rounded-xl bg-stone-200 p-1 text-sm">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => switchTab(t.id)}
            className={`rounded-lg px-2 py-2 font-medium ${tab === t.id ? 'bg-white shadow-sm' : 'text-stone-600'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-stone-200 bg-white p-4">
        {tab === 'type' && (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder={PLACEHOLDER}
            className="w-full resize-y rounded-lg border border-stone-300 p-3 font-mono text-sm focus:border-brand-500 focus:outline-none"
          />
        )}
        {tab === 'upload' && (
          <FilePicker
            accept="image/jpeg,image/png,image/webp,application/pdf,.docx,audio/*"
            hint="Photo, PDF, Word (.docx) or audio file, up to 20 MB"
            file={file}
            onChange={setFile}
          />
        )}
        {tab === 'photo' && (
          <FilePicker accept="image/*" capture hint="Snap your handwritten list" file={file} onChange={setFile} />
        )}
        {tab === 'voice' && <VoiceRecorder onRecorded={setAudio} />}
      </div>

      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <button
        onClick={submit}
        disabled={!ready || busy}
        className="mt-6 w-full rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? 'Reading your list…' : 'Read my list'}
      </button>
    </div>
  )
}

function FilePicker(props: {
  accept: string
  hint: string
  capture?: boolean
  file: File | null
  onChange: (f: File | null) => void
}) {
  const preview = props.file?.type.startsWith('image/') ? URL.createObjectURL(props.file) : null
  return (
    <label className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-stone-300 p-6 text-center hover:border-brand-500">
      {preview ? (
        <img src={preview} alt="Selected list" className="max-h-64 rounded" onLoad={() => URL.revokeObjectURL(preview)} />
      ) : (
        <span className="text-4xl" aria-hidden>
          {props.capture ? '📷' : '📄'}
        </span>
      )}
      <span className="font-medium">{props.file ? props.file.name : props.capture ? 'Open camera' : 'Choose a file'}</span>
      <span className="text-xs text-stone-500">{props.hint}</span>
      <input
        type="file"
        accept={props.accept}
        capture={props.capture ? 'environment' : undefined}
        className="sr-only"
        onChange={(e) => props.onChange(e.target.files?.[0] ?? null)}
      />
    </label>
  )
}
