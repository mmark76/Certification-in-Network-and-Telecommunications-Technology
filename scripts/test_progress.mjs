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
const domainModuleIds = [
  ['MOD-01'],
  ['MOD-02', 'MOD-17', 'MOD-18'],
  ['MOD-03', 'MOD-23'],
  ['MOD-19', 'MOD-20'],
  ['MOD-21', 'MOD-22'],
  ['MOD-04', 'MOD-05'],
  ['MOD-06', 'MOD-07', 'MOD-08'],
  ['MOD-09', 'MOD-11'],
  ['MOD-10', 'MOD-12', 'MOD-13', 'MOD-24'],
  ['MOD-14', 'MOD-15', 'MOD-16']
];
const moduleDomains = new Map(
  domainModuleIds.flatMap((moduleIds, domainIndex) => (
    moduleIds.map((moduleId) => [moduleId, `DOMAIN-${String(domainIndex + 1).padStart(2, '0')}`])
  ))
);
const projectedModules = Array.from({ length: 24 }, (_, index) => {
  const order = index + 1;
  const id = `MOD-${String(order).padStart(2, '0')}`;
  return {
    id,
    order,
    title_el: `Module ${order}`,
    domain_id: moduleDomains.get(id),
    available: id === 'MOD-01',
    status: id === 'MOD-01' ? 'needs_verification' : 'planned',
    lesson_html: id === 'MOD-01' ? 'lesson-digital-logic.html' : null
  };
});
const documentStub = {
  documentElement: { dataset: {} },
  querySelector: () => null,
  querySelectorAll: () => []
};
const windowStub = {
  __NTT_TESTING__: true,
  NTT_CURRICULUM: {
    version: 1,
    domains: domainModuleIds.map((moduleIds, index) => ({
      id: `DOMAIN-${String(index + 1).padStart(2, '0')}`,
      order: index + 1,
      title: `Domain ${index + 1}`,
      guiding_question: `Guiding question ${index + 1}?`,
      module_ids: moduleIds
    })),
    modules: projectedModules
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
const curriculum = api.readCurriculum();
assert.equal(curriculum.domains.length, 10);
assert.equal(curriculum.modules.length, 24);

const progress = api.createDefaultProgress();
assert.equal(Object.keys(progress.modules).length, 24);
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
assert.equal(Object.keys(normalized.modules).length, 24);
assert.deepEqual(plain(normalized.modules['MOD-01']), {
  lessonCompleted: true,
  quizScore: 100,
  labCompleted: false,
  reviewCompleted: false
});
assert.deepEqual(plain(normalized.modules['MOD-24']), {
  lessonCompleted: false,
  quizScore: 0,
  labCompleted: false,
  reviewCompleted: false
});
assert.equal(
  api.calculatePercent(normalized),
  60,
  'Adding planned modules must not reinterpret MOD-01 progress.'
);

storage.clear();
storage.setItem('nt-certification-progress-v2', 'null');
storage.setItem('nt-certification-progress-v1', '[]');
const safeDefault = api.readProgress();
assert.equal(safeDefault.version, 2);
assert.equal(api.calculatePercent(safeDefault), 0);

storage.clear();
api.writeProgress(progress);
assert.deepEqual(plain(api.readProgress()), plain(progress));

storage.setItem('nt-certification-progress-v2', '{"version":2}');
storage.setItem('nt-certification-progress-v1', '{"completedLessons":[]}');
storage.setItem('ntt-flashcard-confidence-v1', '{"GEN-101":"known"}');
storage.setItem('nt-certification-interface-v2', '{"theme":"dark"}');
api.clearSavedLearningData();
assert.equal(storage.getItem('nt-certification-progress-v2'), null);
assert.equal(storage.getItem('nt-certification-progress-v1'), null);
assert.equal(storage.getItem('ntt-flashcard-confidence-v1'), null);
assert.equal(
  storage.getItem('nt-certification-interface-v2'),
  '{"theme":"dark"}',
  'Clearing learning data must preserve interface settings.'
);

console.log('Progress contract tests passed: migration, recovery, persistence and weights.');
