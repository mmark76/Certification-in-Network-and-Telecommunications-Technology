(() => {
  'use strict';

  const STORAGE_KEY = 'nt-certification-progress-v1';
  const SETTINGS_KEY = 'nt-certification-interface-v2';
  const SITE_VERSION = 'v 0.1.0_20260725_1915_75748d6';
  const DELTA_360_PDF = 'https://www.iekdelta360.edu.gr/files/repository/eoppep/%CE%99%CE%95%CE%9A-%CE%94%CE%95%CE%9B%CE%A4%CE%91-360-technikos-diktion.pdf';

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
      // The website remains usable when local storage is unavailable.
    }
  };

  const readSettings = () => ({
    ...DEFAULT_SETTINGS,
    ...safeRead(SETTINGS_KEY, DEFAULT_SETTINGS)
  });

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

  const createOption = (value, label) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    return option;
  };

  const createSettingRow = ({ id, label, description, value, options }) => {
    const row = document.createElement('label');
    row.className = 'settings-row';
    row.htmlFor = id;

    const labelWrap = document.createElement('span');
    labelWrap.className = 'settings-row__label';

    const labelText = document.createElement('strong');
    labelText.textContent = label;
    labelWrap.appendChild(labelText);

    if (description) {
      const help = document.createElement('small');
      help.textContent = description;
      labelWrap.appendChild(help);
    }

    const select = document.createElement('select');
    select.id = id;
    select.name = id;
    options.forEach(([optionValue, optionLabel]) => {
      select.appendChild(createOption(optionValue, optionLabel));
    });
    select.value = value;

    row.append(labelWrap, select);
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
    title.textContent = 'Settings';
    const intro = document.createElement('p');
    intro.textContent = 'Προσάρμοσε την εμφάνιση και τη συμπεριφορά του εκπαιδευτικού εργαλείου.';
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

    const definitions = [
      {
        key: 'theme',
        id: 'setting-theme',
        label: 'Θέμα',
        description: 'Αυτόματο, φωτεινό ή σκοτεινό.',
        options: [['system', 'Σύστημα'], ['light', 'Φωτεινό'], ['dark', 'Σκοτεινό']]
      },
      {
        key: 'accent',
        id: 'setting-accent',
        label: 'Χρώμα έμφασης',
        description: 'Κύρια χρωματική ταυτότητα.',
        options: [['steel', 'Steel'], ['teal', 'Teal'], ['blue', 'Blue'], ['indigo', 'Indigo'], ['green', 'Green']]
      },
      {
        key: 'font',
        id: 'setting-font',
        label: 'Γραμματοσειρά',
        description: 'Τύπος γραμματοσειράς ανάγνωσης.',
        options: [['sans', 'Sans serif'], ['serif', 'Serif'], ['system', 'System UI'], ['mono', 'Monospace']]
      },
      {
        key: 'textSize',
        id: 'setting-text-size',
        label: 'Μέγεθος κειμένου',
        description: 'Γενική κλίμακα γραμματοσειράς.',
        options: [['small', 'Μικρό'], ['default', 'Κανονικό'], ['large', 'Μεγάλο'], ['xlarge', 'Πολύ μεγάλο']]
      },
      {
        key: 'contentWidth',
        id: 'setting-content-width',
        label: 'Πλάτος περιεχομένου',
        description: 'Στενό για ανάγνωση ή ευρύ για πίνακες.',
        options: [['narrow', 'Στενό'], ['standard', 'Κανονικό'], ['wide', 'Ευρύ']]
      },
      {
        key: 'spacing',
        id: 'setting-spacing',
        label: 'Πυκνότητα διάταξης',
        description: 'Από συμπαγή έως πιο άνετη.',
        options: [['compact', 'Συμπαγής'], ['comfortable', 'Άνετη'], ['spacious', 'Ευρύχωρη']]
      },
      {
        key: 'contrast',
        id: 'setting-contrast',
        label: 'Αντίθεση',
        description: 'Ενισχυμένη αντίθεση για καλύτερη ανάγνωση.',
        options: [['standard', 'Κανονική'], ['high', 'Υψηλή']]
      },
      {
        key: 'motion',
        id: 'setting-motion',
        label: 'Κίνηση',
        description: 'Περιορισμός animations και ομαλής κύλισης.',
        options: [['standard', 'Κανονική'], ['reduced', 'Μειωμένη']]
      },
      {
        key: 'sidebar',
        id: 'setting-sidebar',
        label: 'Πλευρική πλοήγηση',
        description: 'Έλεγχος εμφάνισης στα μαθήματα.',
        options: [['auto', 'Αυτόματα'], ['show', 'Πάντα ορατή'], ['hide', 'Κρυφή']]
      }
    ];

    const controls = {};
    const fields = document.createElement('div');
    fields.className = 'settings-fields';

    definitions.forEach((definition) => {
      const control = createSettingRow({
        ...definition,
        value: current[definition.key]
      });
      controls[definition.key] = control.select;
      fields.appendChild(control.row);
    });

    const dataActions = document.createElement('div');
    dataActions.className = 'settings-data-actions';

    const clearProgressButton = document.createElement('button');
    clearProgressButton.type = 'button';
    clearProgressButton.className = 'settings-clear-progress';
    clearProgressButton.textContent = 'Διαγραφή αποθηκευμένης προόδου';
    dataActions.appendChild(clearProgressButton);

    const actions = document.createElement('div');
    actions.className = 'settings-actions';

    const resetButton = document.createElement('button');
    resetButton.type = 'button';
    resetButton.className = 'settings-reset';
    resetButton.textContent = 'Επαναφορά';

    const saveButton = document.createElement('button');
    saveButton.type = 'submit';
    saveButton.className = 'settings-save';
    saveButton.textContent = 'Αποθήκευση';

    actions.append(resetButton, saveButton);
    form.append(fields, dataActions, actions);
    dialog.append(header, form);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    const setControlValues = (settings) => {
      definitions.forEach(({ key }) => {
        controls[key].value = settings[key];
      });
    };

    const collectValues = () => {
      const values = {};
      definitions.forEach(({ key }) => {
        values[key] = controls[key].value;
      });
      return values;
    };

    const openDialog = () => {
      setControlValues(readSettings());
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
      const updated = collectValues();
      safeWrite(SETTINGS_KEY, updated);
      applySettings(updated);
      closeDialog();
    });

    resetButton.addEventListener('click', () => {
      safeWrite(SETTINGS_KEY, DEFAULT_SETTINGS);
      applySettings(DEFAULT_SETTINGS);
      setControlValues(DEFAULT_SETTINGS);
    });

    clearProgressButton.addEventListener('click', () => {
      const confirmed = window.confirm('Να διαγραφεί όλη η αποθηκευμένη πρόοδος και τα αποτελέσματα quiz;');
      if (!confirmed) return;
      localStorage.removeItem(STORAGE_KEY);
      updateProgressUI();
      document.querySelectorAll('[data-lesson-id]').forEach((checkbox) => {
        checkbox.checked = false;
      });
      window.alert('Η αποθηκευμένη πρόοδος διαγράφηκε.');
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
    const stylesheets = ['assets/fixed-layout.css', 'assets/interface-overrides.css'];
    stylesheets.forEach((href) => {
      if (document.querySelector(`link[href="${href}"]`)) return;
      const stylesheet = document.createElement('link');
      stylesheet.rel = 'stylesheet';
      stylesheet.href = href;
      document.head.appendChild(stylesheet);
    });

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
        question.style.borderColor = selected && selected.value === expected ? '#2f7d72' : '#b34a55';
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