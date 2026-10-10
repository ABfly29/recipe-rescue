import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import Header from './components/Header'
import Hero from './components/Hero'
import IngredientChips from './components/IngredientChips'
import RecipeSection from './components/RecipeSection'
import { ingredients, recipes } from './data/recipes'

// "Almost there" = at most this many ingredients missing
const MAX_MISSING = 2

export default function App() {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [searched, setSearched] = useState(false)

  const visibleIngredients = ingredients.filter((i) =>
    `${i.en} ${i.hi}`.toLowerCase().includes(query.trim().toLowerCase()),
  )

  const toggle = (id: string) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  // Compare each recipe's ingredients with what the user picked
  const scored = recipes.map((recipe) => ({
    recipe,
    missing: recipe.ingredients.filter((id) => !selected.includes(id)),
    matched: recipe.ingredients.filter((id) => selected.includes(id)).length,
  }))
  const exact = scored.filter((r) => r.missing.length === 0)
  const almost = scored.filter(
    (r) => r.matched > 0 && r.missing.length > 0 && r.missing.length <= MAX_MISSING,
  )

  return (
    <>
      <Header />
      <main className="mx-auto max-w-5xl px-4 pb-16">
        <Hero query={query} onQueryChange={setQuery} />
        <IngredientChips items={visibleIngredients} selected={selected} onToggle={toggle} />

        <div className="mt-6 flex justify-center">
          <button
            type="button"
            disabled={selected.length === 0}
            onClick={() => setSearched(true)}
            className="flex items-center gap-2 rounded-full bg-leaf px-8 py-3 font-semibold text-white shadow transition hover:bg-leaf-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Sparkles size={18} /> Find Recipes
          </button>
        </div>

        {searched && selected.length > 0 && (
          <>
            <RecipeSection
              title="Exact Matches"
              subtitle="You have everything for these"
              results={exact}
              emptyText="No exact matches yet. Try adding more ingredients."
            />
            <RecipeSection
              title="You're Almost There"
              subtitle={`Just ${MAX_MISSING} or fewer ingredients away`}
              results={almost}
              emptyText="Nothing close yet."
            />
          </>
        )}
      </main>
    </>
  )
}
