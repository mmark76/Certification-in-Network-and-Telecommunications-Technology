(() => {
  'use strict';

  const PROGRESS_STORAGE_KEY = 'nt-certification-progress-v2';
  const LEGACY_PROGRESS_STORAGE_KEY = 'nt-certification-progress-v1';
  const SETTINGS_KEY = 'nt-certification-interface-v2';
  const PASSING_QUIZ_SCORE = 80;
  const DEFAULT_BUILD_INFO = Object.freeze({
    version: '0.1.0',
    buildStamp: 'local',
    shortSha: 'dev'
  });

  const DEFAULT_SETTINGS = {
    theme: 'system',
    accent: 'steel',
    font: 'sans',
    textSize: 'default',
    contentWidth: 'standard',
    spacing: 'comfortable',
    contrast: 'standard',
    motion: 'standard',
    sidebar: 'auto'
  };

  const SETTING_VALUES = {
    theme: new Set(['system', 'light', 'dark']),
    accent: new Set(['steel', 'teal', 'blue', 'indigo', 'green']),
    font: new Set(['sans', 'serif', 'system', 'mono']),
    textSize: new Set(['small', 'default', 'large', 'xlarge']),
    contentWidth: new Set(['narrow', 'standard', 'wide']),
    spacing: new Set(['compact', 'comfortable', 'spacious']),
    contrast: new Set(['standard', 'high']),
    motion: new Set(['standard', 'reduced']),
    sidebar: new Set(['auto', 'show', 'hide'])
  };

  const PROGRESS_FIELDS = new Set([
    'lessonCompleted',
    'labCompleted',
    'reviewCompleted'
  ]);

  const isRecord = (value) => (
    value !== null
    && typeof value === 'object'
    && !Array.isArray(value)
  );

  const readBuildInfo = () => {
    const source = isRecord(window.NTT_BUILD_INFO)
      ? window.NTT_BUILD_INFO
      : {};
    const safePart = (value, fallback) => (
      typeof value === 'string' && value.trim()
        ? value.trim()
        : fallback
    );

    return {
      version: safePart(source.version, DEFAULT_BUILD_INFO.version),
      buildStamp: safePart(source.buildStamp, DEFAULT_BUILD_INFO.buildStamp),
      shortSha: safePart(source.shortSha, DEFAULT_BUILD_INFO.shortSha)
    };
  };

  const updateBuildVersion = () => {
    const versionElement = document.querySelector('[data-build-version]');
    if (!versionElement) return;

    const { version, buildStamp, shortSha } = readBuildInfo();
    versionElement.textContent = `v ${version}_${buildStamp}_${shortSha}`;
  };

  const safeReadStorage = (key) => {
    try {
      const stored = localStorage.getItem(key);
      if (stored === null) return { found: false, value: null };
      return { found: true, value: JSON.parse(stored) };
    } catch {
      return { found: true, value: null };
    }
  };

  const safeWriteStorage = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  };

  const safeRemoveStorage = (key) => {
    try {
      localStorage.removeItem(key);
    } catch {
      // The site remains usable when storage is unavailable.
    }
  };

  const readCurriculum = () => {
    const source = window.NTT_CURRICULUM;
    if (!isRecord(source) || !Array.isArray(source.modules)) {
      return { version: 0, modules: [] };
    }

    const seen = new Set();
    const modules = source.modules.filter((module) => {
      if (
        !isRecord(module)
        || typeof module.id !== 'string'
        || !/^MOD-\d{2}$/.test(module.id)
        || seen.has(module.id)
        || typeof module.available !== 'boolean'
      ) {
        return false;
      }
      seen.add(module.id);
      return true;
    });

    return {
      version: Number.isInteger(source.version) ? source.version : 0,
      modules
    };
  };

  const curriculum = readCurriculum();

  const readSettings = () => {
    const stored = safeReadStorage(SETTINGS_KEY).value;
    if (!isRecord(stored)) return { ...DEFAULT_SETTINGS };

    return Object.fromEntries(
      Object.entries(DEFAULT_SETTINGS).map(([key, fallback]) => [
        key,
        SETTING_VALUES[key].has(stored[key]) ? stored[key] : fallback
      ])
    );
  };

  const applySettings = (settings) => {
    const root = document.documentElement;
    root.dataset.nttTheme = settings.theme;
    root.dataset.nttAccent = settings.accent;
    root.dataset.nttFont = settings.font;
    root.dataset.nttText = settings.textSize;
    root.dataset.nttWidth = settings.contentWidth;
    root.dataset.nttSpacing = settings.spacing;
    root.dataset.nttContrast = settings.contrast;
    root.dataset.nttMotion = settings.motion;
    root.dataset.nttSidebar = settings.sidebar;
  };

  const createEmptyModuleProgress = () => ({
    lessonCompleted: false,
    quizScore: 0,
    labCompleted: false,
    reviewCompleted: false
  });

  const createDefaultProgress = () => ({
    version: 2,
    modules: Object.fromEntries(
      curriculum.modules.map((module) => [module.id, createEmptyModuleProgress()])
    )
  });

  const normalizeScore = (value) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return 0;
    return Math.min(100, Math.max(0, Math.round(value)));
  };

  const normalizeModuleProgress = (value) => {
    const state = isRecord(value) ? value : {};
    return {
      lessonCompleted: state.lessonCompleted === true,
      quizScore: normalizeScore(state.quizScore),
      labCompleted: state.labCompleted === true,
      reviewCompleted: state.reviewCompleted === true
    };
  };

  const normalizeVersionTwoProgress = (value) => {
    if (!isRecord(value) || value.version !== 2 || !isRecord(value.modules)) {
      return null;
    }

    const normalized = createDefaultProgress();
    Object.entries(value.modules).forEach(([moduleId, state]) => {
      if (/^MOD-\d{2}$/.test(moduleId) && isRecord(state)) {
        normalized.modules[moduleId] = normalizeModuleProgress(state);
      }
    });
    return normalized;
  };

  const migrateLegacyProgress = (value) => {
    if (!isRecord(value)) return null;

    const completedLessons = Array.isArray(value.completedLessons)
      ? value.completedLessons.filter((item) => typeof item === 'string')
      : [];
    const quizScores = isRecord(value.quizScores) ? value.quizScores : {};
    const migrated = createDefaultProgress();

    if (!migrated.modules['MOD-01']) {
      migrated.modules['MOD-01'] = createEmptyModuleProgress();
    }

    migrated.modules['MOD-01'] = {
      lessonCompleted: completedLessons.includes('lesson-01-digital-logic'),
      quizScore: normalizeScore(quizScores['quiz-01-binary']),
      labCompleted: completedLessons.includes('lab-01-binary-logic'),
      reviewCompleted: false
    };
    return migrated;
  };

  const readProgress = () => {
    const current = safeReadStorage(PROGRESS_STORAGE_KEY);
    const normalized = normalizeVersionTwoProgress(current.value);
    if (normalized) return normalized;

    const legacy = safeReadStorage(LEGACY_PROGRESS_STORAGE_KEY);
    const migrated = migrateLegacyProgress(legacy.value);
    if (migrated) {
      safeWriteStorage(PROGRESS_STORAGE_KEY, migrated);
      return migrated;
    }

    return createDefaultProgress();
  };

  const writeProgress = (progress) => {
    const normalized = normalizeVersionTwoProgress(progress);
    if (normalized) safeWriteStorage(PROGRESS_STORAGE_KEY, normalized);
  };

  const modulePercent = (state) => {
    let percent = 0;
    if (state.lessonCompleted) percent += 30;
    if (state.quizScore >= PASSING_QUIZ_SCORE) percent += 30;
    if (state.labCompleted) percent += 30;
    if (state.reviewCompleted) percent += 10;
    return percent;
  };

  const calculatePercent = (progress) => {
    const availableModules = curriculum.modules.filter((module) => module.available);
    if (availableModules.length === 0) return 0;

    const total = availableModules.reduce((sum, module) => {
      const state = progress.modules[module.id] || createEmptyModuleProgress();
      return sum + modulePercent(state);
    }, 0);

    return Math.round(total / availableModules.length);
  };

  const updateProgressUI = () => {
    const percent = calculatePercent(readProgress());

    document.querySelectorAll(
      '#home-progress-label, [data-progress-label]'
    ).forEach((element) => {
      element.textContent = `${percent}%`;
    });

    document.querySelectorAll(
      '#home-progress-bar, [data-progress-bar]'
    ).forEach((element) => {
      element.style.width = `${percent}%`;
    });

    document.querySelectorAll('[role="progressbar"]').forEach((element) => {
      element.setAttribute('aria-valuenow', String(percent));
      element.setAttribute('aria-valuetext', `${percent}% συνολική πρόοδος`);
    });
  };

  const syncProgressControls = () => {
    const progress = readProgress();
    document.querySelectorAll(
      'input[type="checkbox"][data-module-id][data-progress-field]'
    ).forEach((checkbox) => {
      const moduleId = checkbox.dataset.moduleId;
      const field = checkbox.dataset.progressField;
      const state = progress.modules[moduleId] || createEmptyModuleProgress();
      checkbox.checked = PROGRESS_FIELDS.has(field) && state[field] === true;
    });
  };

  const resetQuizFeedback = (form) => {
    form.querySelectorAll('[data-answer]').forEach((question) => {
      question.classList.remove('is-correct', 'is-incorrect');
      question.querySelector('.question-feedback')?.remove();
      question.querySelector('fieldset')?.removeAttribute('aria-describedby');
    });

    const result = form.querySelector('.quiz-result');
    if (result) {
      result.replaceChildren();
      result.classList.remove('show');
    }
  };

  const setupSettingsDialog = () => {
    const dialog = document.querySelector('#settings-dialog');
    const settingsButton = document.querySelector('.settings-button');
    if (!dialog || typeof dialog.showModal !== 'function' || !settingsButton) return;

    const form = dialog.querySelector('.settings-form');
    const closeButton = dialog.querySelector('[data-dialog-close]');
    const resetButton = dialog.querySelector('[data-settings-reset]');
    const clearProgressButton = dialog.querySelector('[data-clear-progress]');
    const controls = [...dialog.querySelectorAll('select[data-setting]')];
    let opener = null;

    const setControlValues = (settings) => {
      controls.forEach((control) => {
        const key = control.dataset.setting;
        if (key in settings) control.value = settings[key];
      });
    };

    const collectValues = () => {
      const values = {};
      controls.forEach((control) => {
        values[control.dataset.setting] = control.value;
      });
      return values;
    };

    settingsButton.addEventListener('click', () => {
      opener = settingsButton;
      setControlValues(readSettings());
      document.body.classList.add('settings-open');
      dialog.showModal();
      controls[0]?.focus();
    });

    closeButton?.addEventListener('click', () => dialog.close());

    dialog.addEventListener('close', () => {
      document.body.classList.remove('settings-open');
      opener?.focus();
    });

    form?.addEventListener('submit', (event) => {
      event.preventDefault();
      const candidate = collectValues();
      const validated = Object.fromEntries(
        Object.entries(DEFAULT_SETTINGS).map(([key, fallback]) => [
          key,
          SETTING_VALUES[key].has(candidate[key]) ? candidate[key] : fallback
        ])
      );
      safeWriteStorage(SETTINGS_KEY, validated);
      applySettings(validated);
      dialog.close();
    });

    resetButton?.addEventListener('click', () => {
      safeWriteStorage(SETTINGS_KEY, DEFAULT_SETTINGS);
      applySettings(DEFAULT_SETTINGS);
      setControlValues(DEFAULT_SETTINGS);
      controls[0]?.focus();
    });

    clearProgressButton?.addEventListener('click', () => {
      const confirmed = window.confirm(
        'Να διαγραφεί όλη η αποθηκευμένη πρόοδος και τα αποτελέσματα quiz;'
      );
      if (!confirmed) return;

      safeRemoveStorage(PROGRESS_STORAGE_KEY);
      safeRemoveStorage(LEGACY_PROGRESS_STORAGE_KEY);
      syncProgressControls();
      document.querySelectorAll('[data-quiz]').forEach(resetQuizFeedback);
      updateProgressUI();
      window.alert('Η αποθηκευμένη πρόοδος διαγράφηκε.');
    });
  };

  const setupNavigation = () => {
    const toggle = document.querySelector('.nav-toggle');
    const nav = document.querySelector('.main-nav');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });

    nav.addEventListener('click', () => {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  };

  const setupProgressControls = () => {
    const controls = document.querySelectorAll(
      'input[type="checkbox"][data-module-id][data-progress-field]'
    );

    syncProgressControls();
    controls.forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        const moduleId = checkbox.dataset.moduleId;
        const field = checkbox.dataset.progressField;
        if (!PROGRESS_FIELDS.has(field)) return;

        const progress = readProgress();
        if (!progress.modules[moduleId]) {
          progress.modules[moduleId] = createEmptyModuleProgress();
        }
        progress.modules[moduleId][field] = checkbox.checked;
        writeProgress(progress);
        updateProgressUI();
      });
    });
  };

  const setupQuiz = () => {
    document.querySelectorAll('[data-quiz][data-module-id]').forEach((form) => {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        resetQuizFeedback(form);

        const questions = [...form.querySelectorAll('[data-answer]')];
        let score = 0;
        let firstIncorrect = null;

        questions.forEach((question, index) => {
          const expected = question.dataset.answer;
          const selected = question.querySelector('input:checked');
          const correct = Boolean(selected && selected.value === expected);
          const questionId = question.dataset.questionId || `question-${index + 1}`;
          const feedback = document.createElement('p');
          const fieldset = question.querySelector('fieldset');
          const feedbackDetail = selected?.dataset.feedback?.trim();
          const feedbackLead = correct
            ? 'Σωστή απάντηση.'
            : selected
              ? 'Λανθασμένη απάντηση.'
              : 'Δεν επιλέχθηκε απάντηση.';

          feedback.className = 'question-feedback';
          feedback.id = `${form.dataset.quiz}-${questionId}-feedback`;
          feedback.textContent = feedbackDetail
            ? `${feedbackLead} ${feedbackDetail}`
            : feedbackLead;

          question.classList.add(correct ? 'is-correct' : 'is-incorrect');
          question.appendChild(feedback);
          fieldset?.setAttribute('aria-describedby', feedback.id);

          if (correct) {
            score += 1;
          } else if (!firstIncorrect) {
            firstIncorrect = fieldset || question;
          }
        });

        const percent = questions.length === 0
          ? 0
          : Math.round((score / questions.length) * 100);
        const result = form.querySelector('.quiz-result');
        if (result) {
          const summary = document.createElement('strong');
          const message = document.createTextNode(
            percent >= PASSING_QUIZ_SCORE
              ? ' Επιτυχία. Συνέχισε με το εργαστήριο και την επανάληψη.'
              : ' Χρειάζεται επανάληψη στα λάθη πριν από νέα προσπάθεια.'
          );
          summary.textContent = `Αποτέλεσμα: ${score}/${questions.length} (${percent}%).`;
          result.replaceChildren(summary, message);
          result.classList.add('show');
        }

        const progress = readProgress();
        const moduleId = form.dataset.moduleId;
        if (!progress.modules[moduleId]) {
          progress.modules[moduleId] = createEmptyModuleProgress();
        }
        progress.modules[moduleId].quizScore = percent;
        writeProgress(progress);
        updateProgressUI();

        if (firstIncorrect) {
          firstIncorrect.tabIndex = -1;
          firstIncorrect.focus();
        }
      });
    });
  };

  if (window.__NTT_TESTING__ === true) {
    window.NTT_TEST_API = Object.freeze({
      createDefaultProgress,
      normalizeVersionTwoProgress,
      migrateLegacyProgress,
      readProgress,
      writeProgress,
      modulePercent,
      calculatePercent
    });
  }

  applySettings(readSettings());
  updateBuildVersion();
  setupSettingsDialog();
  setupNavigation();
  setupProgressControls();
  setupQuiz();
  updateProgressUI();
})();
