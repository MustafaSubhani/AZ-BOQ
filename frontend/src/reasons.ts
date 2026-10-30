export const REVIEW_REASON: Record<string, string> = {
  hand_link: 'Review required · linked by hand',
  estimator_factor: "Review required · estimator's factor",
  bill_text_factor: 'Review required · factor from the bill text',
  project_rule: 'Review required · project rule',
  conflict: 'Review required · documents disagree',
  manual: 'Set by hand',
  single_reader: 'Review required · one reader',
  copy_only: "Review required · other order's sheet",
}

export function reasonText(reason: { code: string; accepted_by?: string; link?: string; citation?: string; rule?: string; file?: string }) {
  const head = reason.accepted_by ? `Reviewed by ${reason.accepted_by}` : REVIEW_REASON[reason.code] || reason.code
  const detail = [reason.link, reason.rule, reason.citation, reason.file].filter(Boolean).join(' · ')
  return detail ? `${head} (${detail})` : head
}
