#!/usr/bin/env node

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null;
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }

  clear() {
    this.values.clear();
  }
}

const storage = new MemoryStorage();
const documentStub = {
  documentElement: { dataset: {} },
  querySelector: () => null,
  querySelectorAll: () => []
};
const windowStub = {
  __NTT_TESTING__: true,
  NTT_CURRICULUM: {
    version: 1,
    modules: [
      { id: 'MOD-01', order: 1, title_el: 'Module 1', available: true },
      { id: 'MOD-02', order: 2, title_el: 'Module 2', available: false }
    ]
  }
};

runInNewContext(
  readFileSync(new URL('../assets/app.js', import.meta.url), 'utf8'),
  {
    window: windowStub,
    document: documentStub,
    localStorage: storage,
    console
  },
  { filename: 'assets/app.js' }
);

const api = windowStub.NTT_TEST_API;
assert.ok(api, 'The guarded progress test API must be available.');

const plain = (value) => JSON.parse(JSON.stringify(value));
const progress = api.createDefaultProgress();
assert.equal(api.calculatePercent(progress), 0);

progress.modules['MOD-02'] = {
  lessonCompleted: true,
  quizScore: 100,
  labCompleted: true,
  reviewCompleted: true
};
assert.equal(
  api.calculatePercent(progress),
  0,
  'Unavailable modules must not affect progress.'
);

progress.modules['MOD-01'].lessonCompleted = true;
assert.equal(api.calculatePercent(progress), 30);
progress.modules['MOD-01'].quizScore = 79;
assert.equal(api.calculatePercent(progress), 30);
progress.modules['MOD-01'].quizScore = 80;
assert.equal(api.calculatePercent(progress), 60);
progress.modules['MOD-01'].labCompleted = true;
assert.equal(api.calculatePercent(progress), 90);
progress.modules['MOD-01'].reviewCompleted = true;
assert.equal(api.calculatePercent(progress), 100);

const migrated = api.migrateLegacyProgress({
  completedLessons: ['lesson-01-digital-logic', 'lab-01-binary-logic'],
  quizScores: { 'quiz-01-binary': 88 }
});
assert.deepEqual(plain(migrated.modules['MOD-01']), {
  lessonCompleted: true,
  quizScore: 88,
  labCompleted: true,
  reviewCompleted: false
});

storage.clear();
storage.setItem('nt-certification-progress-v2', '{corrupted json');
storage.setItem(
  'nt-certification-progress-v1',
  JSON.stringify({
    completedLessons: ['lesson-01-digital-logic'],
    quizScores: { 'quiz-01-binary': 80 }
  })
);
const recovered = api.readProgress();
assert.equal(recovered.modules['MOD-01'].lessonCompleted, true);
assert.equal(recovered.modules['MOD-01'].quizScore, 80);
assert.ok(
  storage.getItem('nt-certification-progress-v1'),
  'Migration must preserve the legacy value.'
);
assert.ok(
  storage.getItem('nt-certification-progress-v2'),
  'Migration must persist the version 2 value.'
);

storage.clear();
storage.setItem(
  'nt-certification-progress-v2',
  JSON.stringify({
    version: 2,
    modules: {
      'MOD-01': {
        lessonCompleted: true,
        quizScore: 140,
        labCompleted: 'invalid',
        reviewCompleted: false
      }
    }
  })
);
const normalized = api.readProgress();
assert.deepEqual(plain(normalized.modules['MOD-01']), {
  lessonCompleted: true,
  quizScore: 100,
  labCompleted: false,
  reviewCompleted: false
});

storage.clear();
storage.setItem('nt-certification-progress-v2', 'null');
storage.setItem('nt-certification-progress-v1', '[]');
const safeDefault = api.readProgress();
assert.equal(safeDefault.version, 2);
assert.equal(api.calculatePercent(safeDefault), 0);

storage.clear();
api.writeProgress(progress);
assert.deepEqual(plain(api.readProgress()), plain(progress));

console.log('Progress contract tests passed: migration, recovery, persistence and weights.');
