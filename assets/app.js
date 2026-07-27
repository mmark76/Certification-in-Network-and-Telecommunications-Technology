(() => {
  'use strict';

  const PROGRESS_STORAGE_KEY = 'nt-certification-progress-v2';
  const LEGACY_PROGRESS_STORAGE_KEY = 'nt-certification-progress-v1';
  const FLASHCARD_STORAGE_KEY = 'ntt-flashcard-confidence-v1';
  const FLASHCARD_CLEAR_EVENT = 'ntt:flashcard-confidence-cleared';
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
  const DISPLAY_CODE_PATTERN = /^(?:0[1-9]|10)\.(?:0[1-9]|[1-9]\d)$/;

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

  const clearSavedLearningData = () => {
    safeRemoveStorage(PROGRESS_STORAGE_KEY);
    safeRemoveStorage(LEGACY_PROGRESS_STORAGE_KEY);
    safeRemoveStorage(FLASHCARD_STORAGE_KEY);

    if (
      typeof document.dispatchEvent === 'function'
      && typeof Event === 'function'
    ) {
      document.dispatchEvent(new Event(FLASHCARD_CLEAR_EVENT));
    }
  };

  const readCurriculum = (source = window.NTT_CURRICULUM) => {
    if (
      !isRecord(source)
      || !Array.isArray(source.domains)
      || !Array.isArray(source.modules)
    ) {
      return { version: 0, domains: [], modules: [] };
    }

    const moduleIds = new Set();
    const moduleOrders = new Set();
    const displayCodes = new Set();
    let modulesAreValid = true;
    const modules = [];
    source.modules.forEach((module) => {
      if (
        !isRecord(module)
        || typeof module.id !== 'string'
        || !/^MOD-(?:0[1-9]|1\d|2[0-4])$/.test(module.id)
        || moduleIds.has(module.id)
        || !Number.isInteger(module.order)
        || moduleOrders.has(module.order)
        || typeof module.display_code !== 'string'
        || !DISPLAY_CODE_PATTERN.test(module.display_code)
        || displayCodes.has(module.display_code)
        || typeof module.title_el !== 'string'
        || !module.title_el.trim()
        || typeof module.domain_id !== 'string'
        || !/^DOMAIN-(?:0[1-9]|10)$/.test(module.domain_id)
        || typeof module.available !== 'boolean'
        || typeof module.status !== 'string'
        || !module.status.trim()
        || (
          module.lesson_html !== null
          && (
            typeof module.lesson_html !== 'string'
            || !module.lesson_html.trim()
          )
        )
      ) {
        modulesAreValid = false;
        return;
      }

      moduleIds.add(module.id);
      moduleOrders.add(module.order);
      displayCodes.add(module.display_code);
      modules.push({
        ...module,
        title_el: module.title_el.trim(),
        status: module.status.trim(),
        lesson_html: typeof module.lesson_html === 'string'
          ? module.lesson_html.trim()
          : null
      });
    });

    const domainIds = new Set();
    const domainOrders = new Set();
    let domainsAreValid = true;
    const domains = [];
    source.domains.forEach((domain) => {
      const uniqueModuleIds = Array.isArray(domain?.module_ids)
        ? new Set(domain.module_ids)
        : null;
      if (
        !isRecord(domain)
        || typeof domain.id !== 'string'
        || !/^DOMAIN-(?:0[1-9]|10)$/.test(domain.id)
        || domainIds.has(domain.id)
        || !Number.isInteger(domain.order)
        || domainOrders.has(domain.order)
        || typeof domain.title !== 'string'
        || !domain.title.trim()
        || typeof domain.guiding_question !== 'string'
        || !domain.guiding_question.trim()
        || !Array.isArray(domain.module_ids)
        || domain.module_ids.length === 0
        || domain.module_ids.some(
          (moduleId) => (
            typeof moduleId !== 'string'
            || !/^MOD-(?:0[1-9]|1\d|2[0-4])$/.test(moduleId)
          )
        )
        || uniqueModuleIds.size !== domain.module_ids.length
      ) {
        domainsAreValid = false;
        return;
      }

      domainIds.add(domain.id);
      domainOrders.add(domain.order);
      domains.push({
        ...domain,
        title: domain.title.trim(),
        guiding_question: domain.guiding_question.trim(),
        module_ids: [...domain.module_ids]
      });
    });

    const owners = new Map();
    const domainsById = new Map(
      domains.map((domain) => [domain.id, domain])
    );
    domains.forEach((domain) => {
      domain.module_ids.forEach((moduleId) => {
        owners.set(moduleId, [...(owners.get(moduleId) || []), domain.id]);
      });
    });
    const hierarchyIsValid = (
      modulesAreValid
      && domainsAreValid
      && modules.length > 0
      && domains.length > 0
      && modules.every((module) => {
        const moduleOwners = owners.get(module.id) || [];
        const owner = domainsById.get(module.domain_id);
        const modulePosition = owner?.module_ids.indexOf(module.id) ?? -1;
        const expectedDisplayCode = owner && modulePosition >= 0
          ? `${String(owner.order).padStart(2, '0')}.${String(modulePosition + 1).padStart(2, '0')}`
          : null;
        return (
          moduleOwners.length === 1
          && moduleOwners[0] === module.domain_id
          && module.display_code === expectedDisplayCode
          && module.domain_id === `DOMAIN-${module.display_code.slice(0, 2)}`
        );
      })
      && [...owners].every(
        ([moduleId, moduleOwners]) => (
          moduleIds.has(moduleId)
          && moduleOwners.length === 1
        )
      )
    );

    modules.sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
    domains.sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));

    return {
      version: Number.isInteger(source.version) ? source.version : 0,
      domains: hierarchyIsValid ? domains : [],
      modules
    };
  };

  const curriculum = readCurriculum();

  const formatOrder = (value) => String(value).padStart(2, '0');

  const safeLessonHref = (value) => {
    if (typeof value !== 'string' || !value.endsWith('.html')) return null;
    if (
      value.startsWith('/')
      || value.includes('\\')
      || value.split('/').includes('..')
      || /^[A-Za-z][A-Za-z\d+.-]*:/.test(value)
    ) {
      return null;
    }
    return value;
  };

  const createStatusMessage = (text) => {
    const message = document.createElement('p');
    message.className = 'curriculum-message';
    message.setAttribute('role', 'status');
    message.textContent = text;
    return message;
  };

  const createModuleCard = (module) => {
    const card = document.createElement('article');
    card.className = 'module-card';
    card.dataset.moduleId = module.id;
    card.dataset.available = String(module.available);
    card.dataset.status = module.status;

    const header = document.createElement('header');
    const titleWrapper = document.createElement('div');
    titleWrapper.className = 'module-card__title';
    const title = document.createElement('h3');
    title.textContent = `${module.display_code} · ${module.title_el}`;
    titleWrapper.appendChild(title);

    const status = document.createElement('span');
    status.className = `status${module.available ? ' ready' : ''}`;
    status.textContent = module.available
      ? module.status === 'needs_verification'
        ? 'Διαθέσιμο · προς επαλήθευση'
        : 'Διαθέσιμο'
      : module.status === 'planned'
        ? 'Προγραμματισμένο'
        : 'Μη διαθέσιμο';
    header.append(titleWrapper, status);
    card.appendChild(header);

    const lessonHref = module.available
      ? safeLessonHref(module.lesson_html)
      : null;
    if (lessonHref) {
      const lessonLink = document.createElement('a');
      lessonLink.className = 'text-link module-card__link';
      lessonLink.href = lessonHref;
      lessonLink.textContent = 'Άνοιξε το μάθημα →';
      lessonLink.setAttribute(
        'aria-label',
        `Άνοιξε το μάθημα: ${module.title_el}`
      );
      card.appendChild(lessonLink);
    }

    return card;
  };

  const setupCurriculumViews = () => {
    const navigation = document.querySelector('[data-domain-navigation]');
    const curriculumHost = document.querySelector('[data-curriculum-domains]');
    const homeHost = document.querySelector('[data-home-domains]');
    if (!navigation && !curriculumHost && !homeHost) return;

    if (curriculum.domains.length === 0) {
      const message = 'Ο χάρτης ύλης δεν είναι προσωρινά διαθέσιμος.';
      navigation?.replaceChildren(createStatusMessage(message));
      curriculumHost?.replaceChildren(createStatusMessage(message));
      homeHost?.replaceChildren(createStatusMessage(message));
      return;
    }

    const modulesById = new Map(
      curriculum.modules.map((module) => [module.id, module])
    );

    if (navigation) {
      const fragment = document.createDocumentFragment();
      curriculum.domains.forEach((domain) => {
        const link = document.createElement('a');
        link.href = `#${domain.id.toLowerCase()}`;
        link.textContent = `${formatOrder(domain.order)} · ${domain.title}`;
        fragment.appendChild(link);
      });
      navigation.replaceChildren(fragment);
    }

    if (curriculumHost) {
      const fragment = document.createDocumentFragment();
      curriculum.domains.forEach((domain) => {
        const section = document.createElement('section');
        const headingId = `${domain.id.toLowerCase()}-title`;
        section.id = domain.id.toLowerCase();
        section.className = 'curriculum-domain';
        section.dataset.domainSection = '';
        section.dataset.domainId = domain.id;
        section.setAttribute('aria-labelledby', headingId);

        const eyebrow = document.createElement('p');
        eyebrow.className = 'eyebrow';
        eyebrow.textContent = `Τομέας ${formatOrder(domain.order)}`;

        const heading = document.createElement('h2');
        heading.id = headingId;
        heading.textContent = domain.title;

        const guidingQuestion = document.createElement('p');
        guidingQuestion.className = 'domain-guiding-question';
        const label = document.createElement('strong');
        label.textContent = 'Καθοδηγητική ερώτηση: ';
        guidingQuestion.append(label, domain.guiding_question);

        const moduleList = document.createElement('div');
        moduleList.className = 'module-list';
        const domainModules = domain.module_ids
          .map((moduleId) => modulesById.get(moduleId))
          .filter(Boolean);
        domainModules.forEach((module) => {
          moduleList.appendChild(createModuleCard(module));
        });

        section.append(eyebrow, heading, guidingQuestion, moduleList);
        fragment.appendChild(section);
      });
      curriculumHost.replaceChildren(fragment);
    }

    if (homeHost) {
      const fragment = document.createDocumentFragment();
      curriculum.domains.forEach((domain) => {
        const link = document.createElement('a');
        link.href = `curriculum.html#${domain.id.toLowerCase()}`;
        const order = document.createElement('span');
        order.className = 'topic-grid__order';
        order.textContent = `Τομέας ${formatOrder(domain.order)}`;
        const title = document.createElement('strong');
        title.textContent = domain.title;
        link.append(order, title);
        fragment.appendChild(link);
      });
      homeHost.replaceChildren(fragment);
    }
  };

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
        'Να διαγραφούν η αποθηκευμένη πρόοδος, τα αποτελέσματα quiz και οι αξιολογήσεις flashcards;'
      );
      if (!confirmed) return;

      clearSavedLearningData();
      syncProgressControls();
      document.querySelectorAll('[data-quiz]').forEach(resetQuizFeedback);
      updateProgressUI();
      window.alert('Η αποθηκευμένη πρόοδος και οι αξιολογήσεις flashcards διαγράφηκαν.');
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
      calculatePercent,
      clearSavedLearningData,
      readCurriculum
    });
  }

  applySettings(readSettings());
  updateBuildVersion();
  setupCurriculumViews();
  setupSettingsDialog();
  setupNavigation();
  setupProgressControls();
  setupQuiz();
  updateProgressUI();
})();
