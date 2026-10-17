// Each person has a designated site (the one they work at). Lists across the
// app show that site's items first and highlight them.

/** Classes that highlight a card or row belonging to your designated site. */
export const MY_SITE_HIGHLIGHT = 'ring-2 ring-brand ring-offset-2';

/**
 * Move the items at `siteId` to the front, keeping the order of both groups.
 * @param {object[]} items
 * @param {string|null|undefined} siteId           your designated site (nothing moves without one)
 * @param {(item: object) => string} [siteIdOf]    how to read an item's site (default: item.siteId)
 */
export function mySiteFirst(items, siteId, siteIdOf = (item) => item.siteId) {
  if (!siteId) return items;
  return [...items.filter((item) => siteIdOf(item) === siteId), ...items.filter((item) => siteIdOf(item) !== siteId)];
}
