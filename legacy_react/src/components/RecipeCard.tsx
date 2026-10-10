import { useState } from 'react'
import { Clock } from 'lucide-react'
import { ingredients, type Recipe } from '../data/recipes'

type Props = { recipe: Recipe; missing: string[] }

export default function RecipeCard({ recipe, missing }: Props) {
  const [imageFailed, setImageFailed] = useState(false)
  const missingNames = missing.map((id) => ingredients.find((i) => i.id === id)?.en ?? id)

  return (
    <article className="overflow-hidden rounded-3xl border border-cream-dark bg-white shadow-sm transition hover:shadow-md">
      {imageFailed ? (
        <div className="flex h-40 items-center justify-center bg-cream-dark text-5xl">🍛</div>
      ) : (
        <img
          src={recipe.image}
          alt={recipe.name}
          loading="lazy"
          onError={() => setImageFailed(true)}
          className="h-40 w-full object-cover"
        />
      )}
      <div className="p-4">
        <h3 className="font-display text-lg font-semibold">{recipe.name}</h3>
        <div className="mt-1 flex items-center gap-3 text-sm text-stone-500">
          <span className="flex items-center gap-1"><Clock size={14} /> {recipe.time}</span>
          <span>{recipe.difficulty}</span>
        </div>
        {missingNames.length > 0 && (
          <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Missing: {missingNames.join(', ')}
          </p>
        )}
      </div>
    </article>
  )
}
