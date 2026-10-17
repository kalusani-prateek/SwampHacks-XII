// URL helpers and the page URL map (run: npm test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isSafeInternalPath, isValidSlug, slugify, withQuery } from '../src/utils/url.js';
import { MANAGE_TABS, PATHS, urls } from '../src/routes.js';

test('withQuery drops empty values and keeps slashes readable', () => {
  assert.equal(withQuery('/alerts', { active: false, siteId: undefined }), '/alerts');
  assert.equal(withQuery('/alerts', { active: true, siteId: 'turkey-point' }), '/alerts?active=true&siteId=turkey-point');
  assert.equal(withQuery('/login', { next: '/manage/users' }), '/login?next=/manage/users');
});

test('only same-app paths are allowed as redirects', () => {
  assert.equal(isSafeInternalPath('/manage/users'), true);
  assert.equal(isSafeInternalPath('//evil.example'), false);
  assert.equal(isSafeInternalPath('https://evil.example'), false);
  assert.equal(isSafeInternalPath('/\\evil.example'), false);
  assert.equal(isSafeInternalPath(null), false);
});

test('slugs', () => {
  assert.equal(slugify('Big Cajun II'), 'big-cajun-ii');
  assert.equal(isValidSlug('turkey-point'), true);
  assert.equal(isValidSlug('Turkey Point'), false);
});

test('page URLs are readable and there is no admin section', () => {
  assert.equal(urls.site('turkey-point'), '/sites/turkey-point');
  assert.equal(urls.manage('alert-rules'), '/manage/alert-rules');
  assert.equal(urls.newReport({ site: 'grand-gulf' }), '/reports/new?site=grand-gulf');
  assert.deepEqual(MANAGE_TABS.map((t) => urls.manage(t.slug)).filter((u) => !u.startsWith('/manage/')), []);
  assert.equal(Object.values(PATHS).some((p) => p.includes('admin')), false);
});
