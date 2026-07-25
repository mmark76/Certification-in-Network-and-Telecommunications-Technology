(() => {
  'use strict';

  const STORAGE_KEY = 'nt-certification-progress-v1';

  const readProgress = () => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {
        completedLessons: [],
        quizScores: {}
      };
    } catch {
      return { completedLessons: [], quizScores: {} };
    }
  };

  const writeProgress = (progress) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    } catch {
      // The site remains fully usable if storage is unavailable.
    }
  };

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

  setupNavigation();
  setupLessonCompletion();
  setupQuiz();
  updateProgressUI();
})();
