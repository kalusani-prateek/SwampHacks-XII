// Hazard bands and the demo assistant used when no backend is running (run: npm test).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { getHazardLevel, rankByRisk } from '../src/utils/hazard.js';
import { mockChatReply } from '../src/mocks/chatbot.js';

test('hazard index bands match the backend (GO / CAUTION / NO-GO)', () => {
  assert.equal(getHazardLevel(2).decision, 'GO');
  assert.equal(getHazardLevel(6).decision, 'CAUTION');
  assert.equal(getHazardLevel(9).decision, 'NO-GO');
  assert.deepEqual(rankByRisk([{ hazardIndex: 2 }, { hazardIndex: 8 }]).map((s) => s.hazardIndex), [8, 2]);
});

const ask = (text, siteId = null) => mockChatReply([{ role: 'user', content: text }], siteId);

test('demo assistant: emergencies first, then site-aware answers', () => {
  assert.match(ask('my coworker collapsed'), /^If someone is hurt/);
  assert.match(ask('Is it safe to work here?', 'grand-gulf'), /^Grand Gulf \(MS\)/);
  assert.match(ask('status at turkey point', 'grand-gulf'), /^Turkey Point \(FL\)/);
  assert.match(ask('What is the lightning rule?'), /within 10 miles/);
  assert.match(ask('what is the meaning of life'), /^In demo mode/);
});
