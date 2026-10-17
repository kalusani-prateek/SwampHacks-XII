// Your designated site's items go first; everything else keeps its order.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mySiteFirst } from '../src/utils/mySite.js';

const alerts = [
  { id: 1, siteId: 'grand-gulf' },
  { id: 2, siteId: 'turkey-point' },
  { id: 3, siteId: 'palo-verde' },
  { id: 4, siteId: 'turkey-point' },
];

test('items at your site move to the front, both groups keep their order', () => {
  assert.deepEqual(mySiteFirst(alerts, 'turkey-point').map((a) => a.id), [2, 4, 1, 3]);
});

test('without a designated site nothing moves', () => {
  assert.equal(mySiteFirst(alerts, null), alerts);
  assert.deepEqual(mySiteFirst(alerts, 'nowhere').map((a) => a.id), [1, 2, 3, 4]);
});

test('lists of sites use the site id itself', () => {
  const sites = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
  assert.deepEqual(mySiteFirst(sites, 'c', (s) => s.id).map((s) => s.id), ['c', 'a', 'b']);
});
