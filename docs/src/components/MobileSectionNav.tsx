import type { DocSection, Locale } from '../types/docs'

type MobileSectionNavProps = {
  locale: Locale
  sections: DocSection[]
}

export function MobileSectionNav({ locale, sections }: MobileSectionNavProps) {
  return (
    <section className="mobile-nav card" aria-label={locale === 'vi' ? 'Điều hướng nhanh' : 'Quick navigation'}>
      <p className="mobile-nav-label">{locale === 'vi' ? 'Đi nhanh theo mục' : 'Jump to section'}</p>
      <div className="mobile-nav-scroller">
        <a href="#live-console">{locale === 'vi' ? 'Live Console' : 'Live Console'}</a>
        {sections.map((section) => (
          <a key={section.id} href={`#${section.id}`}>
            {section.title[locale]}
          </a>
        ))}
      </div>
    </section>
  )
}
