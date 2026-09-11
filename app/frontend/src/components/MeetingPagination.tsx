import { useIntl } from "@/contexts/IntlContext";

export function MeetingPagination({ offset, total, limit, onChange, label }: { offset: number; total: number; limit: number; onChange: (value: number) => void; label: string }) {
  const { t, locale } = useIntl();
  if (total <= limit) return null;
  const number = new Intl.NumberFormat(locale);
  return <nav className="pagination" aria-label={label}>
    <button className="button-secondary" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>{t("common.previous")}</button>
    <span>{t("meeting.pageRange", { from: number.format(Math.min(offset + 1, total)), to: number.format(Math.min(offset + limit, total)), total: number.format(total) })}</span>
    <button className="button-secondary" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>{t("common.next")}</button>
  </nav>;
}
