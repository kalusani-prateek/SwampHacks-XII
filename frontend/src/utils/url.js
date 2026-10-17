// URL helpers shared by page routes (src/routes.js) and REST API calls (src/api/).

/**
 * Append a query string, skipping empty values so URLs stay short and readable.
 *   withQuery('/sites', { q: 'florida', page: undefined }) -> '/sites?q=florida'
 *   withQuery('/sites', {})                               -> '/sites'
 * `false` is treated as empty too (omit a boolean filter rather than send "false").
 */
export function withQuery(path, params = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === false) continue;
    search.set(key, String(value));
  }
  // "/" is legal inside a query string (RFC 3986), so keep it unencoded for
  // readability: /login?next=/manage/users instead of next=%2Fmanage%2Fusers.
  const query = search.toString().replace(/%2F/gi, '/');
  return query ? `${path}?${query}` : path;
}

/** Encode one dynamic path segment (an id) so it can never break the URL. */
export const segment = (value) => encodeURIComponent(String(value));

/** IDs used in URLs are lowercase kebab-case, e.g. "turkey-point". */
export const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** True if `value` is a well-formed URL id. */
export function isValidSlug(value) {
  return typeof value === 'string' && SLUG_PATTERN.test(value);
}

/** Make a readable URL id from a name: "Big Cajun II" -> "big-cajun-ii". */
export function slugify(text) {
  return String(text)
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '') // strip accents
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Only allow redirects to paths inside this app. Blocks open redirects such
 * as "//evil.example", "https://evil.example" or "/\evil.example".
 */
export function isSafeInternalPath(path) {
  return typeof path === 'string' && path.startsWith('/') && !path.startsWith('//') && !path.startsWith('/\\');
}
