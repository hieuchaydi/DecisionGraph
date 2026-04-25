import type { DocSection } from '../types/docs'

function toSearchText(section: DocSection): string {
  return [
    section.title.vi,
    section.title.en,
    section.summary?.vi ?? '',
    section.summary?.en ?? '',
    ...(section.bullets?.vi ?? []),
    ...(section.bullets?.en ?? []),
    section.code ?? '',
    section.codeLocalized?.vi ?? '',
    section.codeLocalized?.en ?? '',
  ]
    .join(' ')
    .toLowerCase()
}

export function filterSections(sections: DocSection[], query: string): DocSection[] {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return sections

  return sections.filter((section) => toSearchText(section).includes(normalized))
}
