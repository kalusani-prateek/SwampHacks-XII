// Small label marking items at your designated site (see utils/mySite.js).
export default function MySiteBadge() {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-800">
      📍 Your site
    </span>
  );
}
