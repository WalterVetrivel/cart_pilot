import { useEffect, useRef, useState } from 'react'

const MAX_SECONDS = 60

function pickMimeType(): string {
  const options = ['audio/ogg;codecs=opus', 'audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
  return options.find((t) => MediaRecorder.isTypeSupported(t)) ?? ''
}

export function VoiceRecorder({ onRecorded }: { onRecorded: (blob: Blob | null) => void }) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const timer = useRef<number | null>(null)

  useEffect(() => () => {
    if (timer.current) window.clearInterval(timer.current)
    recorder.current?.stream.getTracks().forEach((t) => t.stop())
  }, [])

  const stop = () => {
    if (timer.current) window.clearInterval(timer.current)
    if (recorder.current?.state === 'recording') recorder.current.stop()
    setRecording(false)
  }

  const start = async () => {
    setError(null)
    onRecorded(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = pickMimeType()
      const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      const chunks: BlobPart[] = []
      rec.ondataavailable = (e) => chunks.push(e.data)
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' })
        setUrl((old) => {
          if (old) URL.revokeObjectURL(old)
          return URL.createObjectURL(blob)
        })
        onRecorded(blob)
      }
      recorder.current = rec
      rec.start()
      setRecording(true)
      setSeconds(0)
      timer.current = window.setInterval(() => {
        setSeconds((s) => {
          if (s + 1 >= MAX_SECONDS) stop()
          return s + 1
        })
      }, 1000)
    } catch {
      setError('Microphone access was blocked. Allow it in your browser and try again.')
    }
  }

  return (
    <div className="flex flex-col items-center gap-4 py-6">
      <button
        type="button"
        onClick={recording ? stop : start}
        className={`flex h-24 w-24 items-center justify-center rounded-full text-sm font-semibold text-white shadow ${
          recording ? 'animate-pulse bg-red-600' : 'bg-brand-600 hover:bg-brand-700'
        }`}
      >
        {recording ? 'Stop' : url ? 'Re-record' : 'Record'}
      </button>
      <p className="text-sm text-stone-600">
        {recording
          ? `Recording… 0:${String(seconds).padStart(2, '0')} / 1:00`
          : 'Speak your list in any language. Up to 60 seconds.'}
      </p>
      {url && !recording && <audio controls src={url} className="w-full" />}
      {error && <p className="text-sm text-red-700">{error}</p>}
    </div>
  )
}
