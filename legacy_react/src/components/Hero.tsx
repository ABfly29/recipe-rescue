import { Search } from 'lucide-react'

type Props = { query: string; onQueryChange: (value: string) => void }

export default function Hero({ query, onQueryChange }: Props) {
  return (
    <section className="px-4 pt-10 pb-6 text-center">
      <h1 className="font-display text-4xl font-bold text-leaf-dark sm:text-5xl">Aaj kya banayein?</h1>
      <p className="mx-auto mt-3 max-w-md text-stone-600">
        Tell us what is in your kitchen and we will rescue dinner with Indian recipes.
      </p>
      <label className="mx-auto mt-6 flex max-w-lg items-center gap-3 rounded-full border border-cream-dark bg-white px-5 py-3 shadow-sm focus-within:ring-2 focus-within:ring-leaf">
        <Search size={20} className="text-stone-400" />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search ingredients, e.g. paneer or आलू"
          className="w-full bg-transparent outline-none placeholder:text-stone-400"
        />
      </label>
    </section>
  )
}
