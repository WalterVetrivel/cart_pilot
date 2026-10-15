import { useState } from 'react'
import { parseList, type ListResponse } from '../lib/api'
import { VoiceRecorder } from './VoiceRecorder'

type Tab = 'type' | 'upload' | 'voice' | 'photo'

const TABS: { id: Tab; label: string }[] = [
  { id: 'type', label: 'Type' },
  { id: 'upload', label: 'Upload' },
  { id: 'voice', label: 'Voice' },
  { id: 'photo', label: 'Photo' },
]

const PLACEHOLDER = `thakkali 1 kg
atta 5 kg
paal 2 litre
toor dal
eggs 1 dozen`

/** Reads a list from text, a file, a voice note or a photo. Appends when listId is given. */
export function ListInput({ listId, onParsed }: { listId?: string; onParsed: (res: ListResponse) => void }) {
  const [tab, setTab] = useState<Tab>('type')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [audio, setAudio] = useState<Blob | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ready =
    (tab === 'type' && text.trim()) || ((tab === 'upload' || tab === 'photo') && file) || (tab === 'voice' && audio)

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      let res: ListResponse
      if (tab === 'type') {
        res = await parseList({ text, listId })
      } else if (tab === 'voice' && audio) {
        const ext = audio.type.includes('ogg') ? 'ogg' : audio.type.includes('mp4') ? 'm4a' : 'webm'
        res = await parseList({ file: audio, filename: `voice.${ext}`, listId })
      } else {
        res = await parseList({ file: file!, filename: file!.name, listId })
      }
      setText('')
      setFile(null)
      setAudio(null)
      onParsed(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div role="tablist" className="grid grid-cols-4 gap-1 rounded-lg bg-stone-100 p-1 text-sm">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => {
              setTab(t.id)
              setFile(null)
              setError(null)
            }}
            className={`rounded-md px-2 py-1.5 font-medium ${tab === t.id ? 'bg-white shadow-sm' : 'text-stone-600 hover:text-stone-900'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-3">
        {tab === 'type' && (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ready && !busy) submit()
            }}
            rows={listId ? 3 : 6}
            placeholder={PLACEHOLDER}
            className="w-full resize-y rounded-lg border border-stone-300 p-3 font-mono text-sm focus:border-brand-500 focus:outline-none"
          />
        )}
        {tab === 'upload' && (
          <FilePicker
            accept="image/jpeg,image/png,image/webp,application/pdf,.docx,audio/*"
            hint="Photo, PDF, Word (.docx) or audio, up to 20 MB"
            file={file}
            onChange={setFile}
          />
        )}
        {tab === 'photo' && (
          <FilePicker accept="image/*" capture hint="Snap a handwritten list" file={file} onChange={setFile} />
        )}
        {tab === 'voice' && <VoiceRecorder onRecorded={setAudio} />}
      </div>

      {error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <button
        onClick={submit}
        disabled={!ready || busy}
        className="mt-3 w-full rounded-lg bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? 'Reading…' : listId ? 'Add to list' : 'Read my list'}
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
    <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-stone-300 p-5 text-center hover:border-brand-500">
      {preview ? (
        <img src={preview} alt="Selected list" className="max-h-48 rounded" onLoad={() => URL.revokeObjectURL(preview)} />
      ) : (
        <span className="text-3xl" aria-hidden>
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
