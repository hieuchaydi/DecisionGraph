import type { DocSection, Locale } from '../types/docs'

type SidebarProps = {
  locale: Locale
  sections: DocSection[]
}

export function Sidebar({ locale, sections }: SidebarProps) {
  return (
    <aside className="sidebar">
      <p className="sidebar-label">{locale === 'vi' ? 'Mục lục' : 'Contents'}</p>
      <nav>
        <a href="#live-console">{locale === 'vi' ? 'Live Readiness Console' : 'Live Readiness Console'}</a>
        {sections.map((section) => (
          <a key={section.id} href={`#${section.id}`}>
            {section.title[locale]}
          </a>
        ))}
      </nav>
    </aside>
  )
}
