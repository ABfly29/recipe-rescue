import type { Recipe } from '../data/recipes'
import RecipeCard from './RecipeCard'

type Props = {
  title: string
  subtitle: string
  results: { recipe: Recipe; missing: string[] }[]
  emptyText: string
}

export default function RecipeSection({ title, subtitle, results, emptyText }: Props) {
  return (
    <section className="mt-10">
      <h2 className="font-display text-2xl font-bold text-leaf-dark">{title}</h2>
      <p className="mb-4 text-sm text-stone-500">{subtitle}</p>
      {results.length === 0 ? (
        <p className="rounded-2xl bg-cream-dark/60 p-6 text-center text-stone-500">{emptyText}</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {results.map(({ recipe, missing }) => (
            <RecipeCard key={recipe.id} recipe={recipe} missing={missing} />
          ))}
        </div>
      )}
    </section>
  )
}
