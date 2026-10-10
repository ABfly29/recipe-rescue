import { ChefHat } from 'lucide-react'

const links = ['Home', 'Recipes', 'Saved', 'About']

export default function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-cream-dark bg-cream/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <a href="/" className="flex items-center gap-2">
          <span className="rounded-xl bg-leaf p-2 text-white">
            <ChefHat size={20} />
          </span>
          <span className="font-display text-lg font-bold text-leaf-dark">Recipe Rescue</span>
        </a>
        <nav className="flex gap-1 text-sm font-medium text-stone-600">
          {links.map((link, i) => (
            <a
              key={link}
              href="#"
              className={`rounded-full px-3 py-1.5 hover:bg-cream-dark ${i > 1 ? 'hidden sm:block' : ''} ${i === 0 ? 'text-leaf-dark' : ''}`}
            >
              {link}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}
