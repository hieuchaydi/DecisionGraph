import type { DocSection, Locale } from '../types/docs'

type DocSectionCardProps = {
  locale: Locale
  section: DocSection
}

export function DocSectionCard({ locale, section }: DocSectionCardProps) {
  return (
    <section id={section.id} className="card">
      <h2>{section.title[locale]}</h2>
      {section.summary ? <p className="summary">{section.summary[locale]}</p> : null}
      {section.bullets ? (
        <ul>
          {section.bullets[locale].map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      {section.code ? (
        <pre>
          <code>{section.code}</code>
        </pre>
      ) : null}
    </section>
  )
}
