import { useState } from 'react'
import { PRESETS, type Preset, type Weights } from '../lib/api'

const PRESET_LABELS: Record<Preset, string> = { cheapest: 'Cheapest', balanced: 'Balanced', fastest: 'Fastest' }
const SLIDERS: { key: keyof Weights; label: string }[] = [
  { key: 'price', label: 'Price' },
  { key: 'rating', label: 'Rating' },
  { key: 'delivery', label: 'Speed' },
  { key: 'availability', label: 'In stock' },
]

function presetOf(w: Weights): Preset | null {
  const match = (Object.keys(PRESETS) as Preset[]).find((p) =>
    SLIDERS.every(({ key }) => Math.abs(PRESETS[p][key] - w[key]) < 0.001),
  )
  return match ?? null
}

interface Props {
  weights: Weights
  onWeights: (w: Weights) => void
}

/** Ranking priority (SPEC §8.2): presets plus sliders. Also decides which product each store contributes to a plan. */
export function DealControls({ weights, onWeights }: Props) {
  const [open, setOpen] = useState(false)
  const active = presetOf(weights)
  const total = SLIDERS.reduce((sum, { key }) => sum + weights[key], 0) || 1

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Priority" className="grid flex-1 grid-cols-3 gap-1 rounded-lg bg-stone-100 p-1 text-sm">
          {(Object.keys(PRESETS) as Preset[]).map((p) => (
            <button
              key={p}
              role="radio"
              aria-checked={active === p}
              onClick={() => onWeights(PRESETS[p])}
              className={`rounded-md px-2 py-1.5 font-medium ${active === p ? 'bg-white shadow-sm' : 'text-stone-600 hover:text-stone-900'}`}
            >
              {PRESET_LABELS[p]}
            </button>
          ))}
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="rounded-lg px-3 py-2 text-sm text-stone-600 hover:bg-stone-100"
        >
          {open ? 'Hide' : 'Adjust'}
          {!active && !open ? ' (custom)' : ''}
        </button>
      </div>

      {open && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {SLIDERS.map(({ key, label }) => (
            <label key={key} className="text-sm">
              <span className="flex justify-between text-stone-600">
                {label}
                <span className="tabular-nums">{Math.round((weights[key] / total) * 100)}%</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={weights[key]}
                onChange={(e) => onWeights({ ...weights, [key]: Number(e.target.value) })}
                className="w-full accent-brand-600"
              />
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
