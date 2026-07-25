(() => {
  'use strict';

  const STORAGE_KEY = 'nt-certification-progress-v1';
  const SETTINGS_KEY = 'nt-certification-interface-v1';
  const SITE_VERSION = 'v 0.1.0_20260725_1905_137c93b';
  const DELTA_360_PDF = 'https://www.iekdelta360.edu.gr/files/repository/eoppep/%CE%99%CE%95%CE%9A-%CE%94%CE%95%CE%9B%CE%A4%CE%91-360-technikos-diktion.pdf';
  const DEFAULT_SETTINGS = {
    theme: 'system',
    textSize: 'default',
    spacing: 'comfortable',
    motion: 'standard'
  };

  const safeRead = (key, fallback) => {
    try {
      return JSON.parse(localStorage.getItem(key)) || fallback;
    } catch {
      return fallback;
    }
  };

  const safeWrite = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // The site remains usable if local storage is unavailable.
    }
  };

  const readSettings = () => ({
    ...DEFAULT_SETTINGS,
    ...safeRead(SETTINGS_KEY, DEFAULT_SETTINGS)
  });

  const applySettings = (settings) => {
    const root = document.documentElement;
    root.dataset.nttTheme = settings.theme;
    root.dataset.nttText = settings.textSize;
    root.dataset.nttSpacing = settings.spacing;
    root.dataset.nttMotion = settings.motion;
  };

  const createOption = (value, label) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    return option;
  };

  const createSettingRow = ({ id, label, value, options }) => {
    const row = document.createElement('label');
    row.className = 'settings-row';
    row.htmlFor = id;

    const labelText = document.createElement('span');
    labelText.textContent = label;

    const select = document.createElement('select');
    select.id = id;
    select.name = id;
    options.forEach(([optionValue, optionLabel]) => {
      select.appendChild(createOption(optionValue, optionLabel));
    });
    select.value = value;

    row.append(labelText, select);
    return { row, select };
  };

  const setupSettingsDialog = (settingsButton) => {
    const overlay = document.createElement('div');
    overlay.className = 'settings-overlay';
    overlay.hidden = true;

    const dialog = document.createElement('section');
    dialog.className = 'settings-dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'settings-title');

    const header = document.createElement('header');
    header.className = 'settings-dialog__header';

    const heading = document.createElement('div');
    const title = document.createElement('h2');
    title.id = 'settings-title';
    title.textContent = 'Interface settings';
    const intro = document.createElement('p');
    intro.textContent = 'Προσάρμοσε την εμφάνιση της εκπαιδευτικής ιστοσελίδας.';
    heading.append(title, intro);

    const closeButton = document.createElement('button');
    closeButton.className = 'settings-close';
    closeButton.type = 'button';
    closeButton.textContent = '×';
    closeButton.setAttribute('aria-label', 'Κλείσιμο ρυθμίσεων');
    header.append(heading, closeButton);

    const form = document.createElement('form');
    form.className = 'settings-form';
    const current = readSettings();

    const theme = createSettingRow({
      id: 'setting-theme',
      label: 'Colour theme',
      value: current.theme,
      options: [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']]
    });
    const textSize = createSettingRow({
      id: 'setting-text-size',
      label: 'Text size',
      value: current.textSize,
      options: [['default', 'Default'], ['large', 'Large']]
    });
    const spacing = createSettingRow({
      id: 'setting-spacing',
      label: 'Layout spacing',
      value: current.spacing,
      options: [['comfortable', 'Comfortable'], ['compact', 'Compact']]
    });
    const motion = createSettingRow({
      id: 'setting-motion',
      label: 'Motion',
      value: current.motion,
      options: [['standard', 'Standard'], ['reduced', 'Reduced']]
    });

    const fields = document.createElement('div');
    fields.className = 'settings-fields';
    fields.append(theme.row, textSize.row, spacing.row, motion.row);

    const actions = document.createElement('div');
    actions.className = 'settings-actions';

    const saveButton = document.createElement('button');
    saveButton.type = 'submit';
    saveButton.className = 'settings-save';
    saveButton.textContent = 'Save settings';

    const resetButton = document.createElement('button');
    resetButton.type = 'button';
    resetButton.className = 'settings-reset';
    resetButton.textContent = 'Reset settings';

    actions.append(saveButton, resetButton);
    form.append(fields, actions);
    dialog.append(header, form);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    const openDialog = () => {
      const saved = readSettings();
      theme.select.value = saved.theme;
      textSize.select.value = saved.textSize;
      spacing.select.value = saved.spacing;
      motion.select.value = saved.motion;
      overlay.hidden = false;
      document.body.classList.add('settings-open');
      closeButton.focus();
    };

    const closeDialog = () => {
      overlay.hidden = true;
      document.body.classList.remove('settings-open');
      settingsButton.focus();
    };

    settingsButton.addEventListener('click', openDialog);
    closeButton.addEventListener('click', closeDialog);
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) closeDialog();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !overlay.hidden) closeDialog();
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const updated = {
        theme: theme.select.value,
        textSize: textSize.select.value,
        spacing: spacing.select.value,
        motion: motion.select.value
      };
      safeWrite(SETTINGS_KEY, updated);
      applySettings(updated);
      closeDialog();
    });

    resetButton.addEventListener('click', () => {
      safeWrite(SETTINGS_KEY, DEFAULT_SETTINGS);
      applySettings(DEFAULT_SETTINGS);
      theme.select.value = DEFAULT_SETTINGS.theme;
      textSize.select.value = DEFAULT_SETTINGS.textSize;
      spacing.select.value = DEFAULT_SETTINGS.spacing;
      motion.select.value = DEFAULT_SETTINGS.motion;
    });
  };

  const setupHeaderControls = () => {
    const navWrap = document.querySelector('.nav-wrap');
    if (!navWrap || navWrap.querySelector('.header-controls')) return;

    const controls = document.createElement('div');
    controls.className = 'header-controls';

    const languagePicker = document.createElement('div');
    languagePicker.className = 'language-picker';

    const languageButton = document.createElement('button');
    languageButton.type = 'button';
    languageButton.className = 'header-action language-button';
    languageButton.textContent = 'EL / GR';
    languageButton.setAttribute('aria-expanded', 'false');
    languageButton.setAttribute('aria-haspopup', 'menu');
    languageButton.setAttribute('aria-label', 'Γλώσσα: Ελληνικά');

    const languageMenu = document.createElement('div');
    languageMenu.className = 'language-menu';
    languageMenu.hidden = true;
    languageMenu.setAttribute('role', 'menu');
    languageMenu.innerHTML = '<span role="menuitem" aria-current="true"><strong>EL / GR</strong><small>Ελληνικά</small><b>✓</b></span>';

    languageButton.addEventListener('click', () => {
      const open = languageMenu.hidden;
      languageMenu.hidden = !open;
      languageButton.setAttribute('aria-expanded', String(open));
    });

    document.addEventListener('click', (event) => {
      if (!languagePicker.contains(event.target)) {
        languageMenu.hidden = true;
        languageButton.setAttribute('aria-expanded', 'false');
      }
    });

    languagePicker.append(languageButton, languageMenu);

    const settingsButton = document.createElement('button');
    settingsButton.type = 'button';
    settingsButton.className = 'header-action settings-button';
    settingsButton.textContent = 'Settings';
    settingsButton.setAttribute('aria-label', 'Άνοιγμα ρυθμίσεων εμφάνισης');

    controls.append(languagePicker, settingsButton);
    navWrap.appendChild(controls);
    setupSettingsDialog(settingsButton);
  };

  const setupFooter = () => {
    const footer = document.querySelector('.site-footer');
    if (!footer) return;

    const copyright = document.createElement('p');
    copyright.className = 'ecosystem-footer__copyright';
    copyright.textContent = `© ${new Date().getFullYear()} Markellos Markides. All rights reserved.`;

    const navigation = document.createElement('nav');
    navigation.className = 'ecosystem-footer__navigation';
    navigation.setAttribute('aria-label', 'Βοηθητικοί σύνδεσμοι');

    const links = [
      ['Markellos Ecosystem', 'https://markellosecosystem.com/', true],
      ['About Markellos', 'https://markellosecosystem.com/about/', true],
      ['Privacy', 'https://markellosecosystem.com/privacy/', true],
      ['Cookies', 'https://markellosecosystem.com/cookies/', true],
      ['Feedback', 'mailto:markellos.markides@gmail.com?subject=NTT%20Certification%20Feedback', false],
      ['iekdelta360pdf', DELTA_360_PDF, true]
    ];

    links.forEach(([label, href, external]) => {
      const link = document.createElement('a');
      link.className = 'ecosystem-footer__link';
      link.href = href;
      link.textContent = label;
      if (label === 'iekdelta360pdf') link.classList.add('footer-pdf-button');
      if (external) {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      }
      navigation.appendChild(link);
    });

    const version = document.createElement('p');
    version.className = 'ecosystem-footer__version';
    version.textContent = SITE_VERSION;
    version.setAttribute('aria-label', `Έκδοση ιστοσελίδας ${SITE_VERSION}`);

    footer.replaceChildren(copyright, navigation, version);
  };

  const setupSiteChrome = () => {
    if (!document.querySelector('link[href="assets/fixed-layout.css"]')) {
      const stylesheet = document.createElement('link');
      stylesheet.rel = 'stylesheet';
      stylesheet.href = 'assets/fixed-layout.css';
      document.head.appendChild(stylesheet);
    }

    document
      .querySelectorAll('.site-header a[href*="github.com"], .site-footer a[href*="github.com"]')
      .forEach((link) => link.remove());

    applySettings(readSettings());
    setupHeaderControls();
    setupFooter();
  };

  const readProgress = () => safeRead(STORAGE_KEY, {
    completedLessons: [],
    quizScores: {}
  });

  const writeProgress = (progress) => safeWrite(STORAGE_KEY, progress);

  const calculatePercent = (progress) => {
    const totalUnits = 16;
    return Math.min(100, Math.round((progress.completedLessons.length / totalUnits) * 100));
  };

  const updateProgressUI = () => {
    const progress = readProgress();
    const percent = calculatePercent(progress);
    const label = document.querySelector('#home-progress-label');
    const bar = document.querySelector('#home-progress-bar');
    if (label) label.textContent = `${percent}%`;
    if (bar) bar.style.width = `${percent}%`;

    document.querySelectorAll('[data-progress-label]').forEach((element) => {
      element.textContent = `${percent}%`;
    });
    document.querySelectorAll('[data-progress-bar]').forEach((element) => {
      element.style.width = `${percent}%`;
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

  const setupLessonCompletion = () => {
    document.querySelectorAll('[data-lesson-id]').forEach((checkbox) => {
      const lessonId = checkbox.dataset.lessonId;
      const progress = readProgress();
      checkbox.checked = progress.completedLessons.includes(lessonId);

      checkbox.addEventListener('change', () => {
        const current = readProgress();
        const set = new Set(current.completedLessons);
        if (checkbox.checked) set.add(lessonId);
        else set.delete(lessonId);
        current.completedLessons = [...set];
        writeProgress(current);
        updateProgressUI();
      });
    });
  };

  const setupQuiz = () => {
    const form = document.querySelector('[data-quiz]');
    if (!form) return;

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const quizId = form.dataset.quiz;
      const questions = [...form.querySelectorAll('[data-answer]')];
      let score = 0;

      questions.forEach((question) => {
        const expected = question.dataset.answer;
        const selected = question.querySelector('input:checked');
        question.style.borderColor = selected && selected.value === expected ? '#00a67e' : '#d33f49';
        if (selected && selected.value === expected) score += 1;
      });

      const percent = Math.round((score / questions.length) * 100);
      const result = form.querySelector('.quiz-result');
      if (result) {
        const message = percent >= 80
          ? 'Επιτυχία. Η ενότητα μπορεί να θεωρηθεί κατακτημένη.'
          : 'Χρειάζεται επανάληψη στα λάθη πριν από νέα προσπάθεια.';
        result.innerHTML = `<strong>Αποτέλεσμα: ${score}/${questions.length} (${percent}%)</strong><br>${message}`;
        result.classList.add('show');
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      const progress = readProgress();
      progress.quizScores[quizId] = percent;
      writeProgress(progress);
    });
  };

  setupSiteChrome();
  setupNavigation();
  setupLessonCompletion();
  setupQuiz();
  updateProgressUI();
})();