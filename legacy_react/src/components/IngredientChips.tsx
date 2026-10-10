import { Check } from 'lucide-react'
import type { Ingredient } from '../data/recipes'

type Props = {
  items: Ingredient[]
  selected: string[]
  onToggle: (id: string) => void
}

export default function IngredientChips({ items, selected, onToggle }: Props) {
  if (items.length === 0) {
    return <p className="text-center text-stone-500">No ingredients match your search.</p>
  }
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {items.map((item) => {
        const active = selected.includes(item.id)
        return (
          <button
            key={item.id}
            type="button"
            aria-pressed={active}
            onClick={() => onToggle(item.id)}
            className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition ${
              active
                ? 'border-leaf bg-leaf text-white'
                : 'border-cream-dark bg-white text-stone-700 hover:border-leaf'
            }`}
          >
            {active ? <Check size={16} /> : <span>{item.emoji}</span>}
            <span className="font-medium">{item.en}</span>
            <span className={active ? 'text-white/80' : 'text-stone-400'}>{item.hi}</span>
          </button>
        )
      })}
    </div>
  )
}
