import { useMemo, useState } from 'react'
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

function App() {
  const [locale, setLocale] = useState<Locale>('vi')
  const [query, setQuery] = useState('')

  const filteredSections = useMemo(() => filterSections(DOC_SECTIONS, query), [query])

  return (
    <div className="docs-shell">
      <TopBar locale={locale} query={query} onQueryChange={setQuery} onLocaleChange={setLocale} />

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
