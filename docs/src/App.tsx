import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { DOC_SECTIONS } from './content/docsContent'
import { DocSectionCard } from './components/DocSectionCard'
import { HeroCard } from './components/HeroCard'
import { MobileSectionNav } from './components/MobileSectionNav'
import { ReadinessConsole } from './components/ReadinessConsole'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import type { Locale } from './types/docs'
import { filterSections } from './utils/filterSections'

type ThemeMode = 'light' | 'dark'

const THEME_STORAGE_KEY = 'decisiongraph.docs.theme'

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'light'

  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY)
  if (storedTheme === 'light' || storedTheme === 'dark') return storedTheme

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function App() {
  const [locale, setLocale] = useState<Locale>('vi')
  const [query, setQuery] = useState('')
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme)

  const filteredSections = useMemo(() => filterSections(DOC_SECTIONS, query), [query])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  return (
    <div className="docs-shell">
      <TopBar
        locale={locale}
        query={query}
        onQueryChange={setQuery}
        onLocaleChange={setLocale}
        theme={theme}
        onThemeToggle={() => setTheme((current) => (current === 'light' ? 'dark' : 'light'))}
      />

      <div className="layout">
        <Sidebar locale={locale} sections={filteredSections} />

        <main className="content">
          <HeroCard locale={locale} />
          <MobileSectionNav locale={locale} sections={filteredSections} />
          <ReadinessConsole locale={locale} />

          {filteredSections.map((section) => (
            <DocSectionCard key={section.id} locale={locale} section={section} />
          ))}
        </main>
      </div>
    </div>
  )
}

export default App
