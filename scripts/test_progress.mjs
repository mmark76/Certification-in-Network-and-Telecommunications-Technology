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
const canonicalDisplayCodes = {
  'MOD-01': '01.01',
  'MOD-02': '02.01',
  'MOD-17': '02.02',
  'MOD-18': '02.03',
  'MOD-03': '03.01',
  'MOD-23': '03.02',
  'MOD-19': '04.01',
  'MOD-20': '04.02',
  'MOD-21': '05.01',
  'MOD-22': '05.02',
  'MOD-04': '06.01',
  'MOD-05': '06.02',
  'MOD-06': '07.01',
  'MOD-07': '07.02',
  'MOD-08': '07.03',
  'MOD-09': '08.01',
  'MOD-11': '08.02',
  'MOD-10': '09.01',
  'MOD-12': '09.02',
  'MOD-13': '09.03',
  'MOD-24': '09.04',
  'MOD-14': '10.01',
  'MOD-15': '10.02',
  'MOD-16': '10.03'
};
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
    display_code: canonicalDisplayCodes[id],
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
const clone = (value) => JSON.parse(JSON.stringify(value));
const curriculum = api.readCurriculum();
assert.equal(curriculum.domains.length, 10);
assert.equal(curriculum.modules.length, 24);
assert.deepEqual(
  Object.fromEntries(
    curriculum.modules.map((module) => [module.id, module.display_code])
  ),
  canonicalDisplayCodes,
  'All 24 technical module IDs must keep their exact hierarchical display codes.'
);
assert.equal(
  new Set(curriculum.modules.map((module) => module.display_code)).size,
  24,
  'All 24 display codes must be unique.'
);
assert.deepEqual(
  plain(
    curriculum.modules.find((module) => module.id === 'MOD-01')
  ),
  {
    id: 'MOD-01',
    order: 1,
    display_code: '01.01',
    title_el: 'Module 1',
    domain_id: 'DOMAIN-01',
    available: true,
    status: 'needs_verification',
    lesson_html: 'lesson-digital-logic.html'
  },
  'MOD-01 must remain available at its existing lesson URL.'
);

const expectInvalidHierarchy = (candidate, message) => {
  const result = api.readCurriculum(candidate);
  assert.equal(result.domains.length, 0, message);
};

const malformedDisplayCode = clone(windowStub.NTT_CURRICULUM);
malformedDisplayCode.modules.find(
  (module) => module.id === 'MOD-17'
).display_code = '2.02';
expectInvalidHierarchy(
  malformedDisplayCode,
  'Single-digit display-code components must invalidate the hierarchy.'
);

const emptyDisplayCode = clone(windowStub.NTT_CURRICULUM);
emptyDisplayCode.modules.find(
  (module) => module.id === 'MOD-17'
).display_code = '';
expectInvalidHierarchy(
  emptyDisplayCode,
  'Empty display codes must invalidate the hierarchy.'
);

const nonStringDisplayCode = clone(windowStub.NTT_CURRICULUM);
nonStringDisplayCode.modules.find(
  (module) => module.id === 'MOD-17'
).display_code = 2.02;
expectInvalidHierarchy(
  nonStringDisplayCode,
  'Non-string display codes must invalidate the hierarchy.'
);

const duplicateDisplayCode = clone(windowStub.NTT_CURRICULUM);
duplicateDisplayCode.modules.find(
  (module) => module.id === 'MOD-17'
).display_code = '02.01';
expectInvalidHierarchy(
  duplicateDisplayCode,
  'Duplicate display codes must invalidate the hierarchy.'
);

const wrongDomainPrefix = clone(windowStub.NTT_CURRICULUM);
wrongDomainPrefix.modules.find(
  (module) => module.id === 'MOD-17'
).display_code = '03.03';
expectInvalidHierarchy(
  wrongDomainPrefix,
  'A display code with the wrong domain prefix must invalidate the hierarchy.'
);

const localNumberingGap = clone(windowStub.NTT_CURRICULUM);
localNumberingGap.modules.find(
  (module) => module.id === 'MOD-18'
).display_code = '02.04';
expectInvalidHierarchy(
  localNumberingGap,
  'A gap in local module numbering must invalidate the hierarchy.'
);

const modulePositionMismatch = clone(windowStub.NTT_CURRICULUM);
modulePositionMismatch.modules.find(
  (module) => module.id === 'MOD-17'
).display_code = '02.03';
modulePositionMismatch.modules.find(
  (module) => module.id === 'MOD-18'
).display_code = '02.02';
expectInvalidHierarchy(
  modulePositionMismatch,
  'Display codes assigned to the wrong domain positions must invalidate the hierarchy.'
);

const progress = api.createDefaultProgress();
assert.equal(Object.keys(progress.modules).length, 24);
assert.deepEqual(
  Object.keys(progress.modules).sort(),
  Array.from({ length: 24 }, (_, index) => (
    `MOD-${String(index + 1).padStart(2, '0')}`
  )),
  'Progress must remain keyed by the permanent MOD-NN technical IDs.'
);
assert.equal(
  Object.values(canonicalDisplayCodes).some(
    (displayCode) => Object.hasOwn(progress.modules, displayCode)
  ),
  false,
  'Learner-facing display codes must never become progress keys.'
);
assert.equal(api.calculatePercent(progress), 0);

const displayCodeIndependentProgress = api.normalizeVersionTwoProgress({
  version: 2,
  modules: {
    'MOD-17': {
      lessonCompleted: true,
      quizScore: 87,
      labCompleted: true,
      reviewCompleted: true
    }
  }
});
assert.deepEqual(
  plain(displayCodeIndependentProgress.modules['MOD-17']),
  {
    lessonCompleted: true,
    quizScore: 87,
    labCompleted: true,
    reviewCompleted: true
  },
  'Existing progress must remain attached to MOD-NN after display codes are introduced.'
);
assert.equal(displayCodeIndependentProgress.modules['02.02'], undefined);

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
