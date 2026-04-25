import type { Locale } from '../types/docs'

type TopBarProps = {
  locale: Locale
  query: string
  onQueryChange: (value: string) => void
  onLocaleChange: (locale: Locale) => void
}

export function TopBar({ locale, query, onQueryChange, onLocaleChange }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <p className="eyebrow">DecisionGraph</p>
        <h1>Docs Hub</h1>
      </div>

      <div className="actions">
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="search"
          placeholder={locale === 'vi' ? 'Tìm nhanh tài liệu...' : 'Search docs quickly...'}
          aria-label="Search documentation"
        />

        <div className="locale">
          <button className={locale === 'vi' ? 'tab active' : 'tab'} type="button" onClick={() => onLocaleChange('vi')}>
            VI
          </button>
          <button className={locale === 'en' ? 'tab active' : 'tab'} type="button" onClick={() => onLocaleChange('en')}>
            EN
          </button>
        </div>
      </div>
    </header>
  )
}
