(() => {
  'use strict';

  const STORAGE_KEY = 'ntt-flashcard-confidence-v1';
  const VALID_STATES = new Set(['known', 'review']);

  const safeRead = () => {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch {
      return {};
    }
  };

  const safeWrite = (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch {
      // Flashcards remain usable when storage is unavailable.
    }
  };

  const state = safeRead();

  const updateSummary = (deck) => {
    const cards = [...deck.querySelectorAll('[data-flashcard-id]')];
    const known = cards.filter((card) => card.dataset.confidence === 'known').length;
    const review = cards.filter((card) => card.dataset.confidence === 'review').length;
    const pending = cards.length - known - review;
    const status = deck.querySelector('[data-flashcard-summary]');
    if (status) {
      status.textContent = `Γνωστές: ${known} · Για επανάληψη: ${review} · Χωρίς αξιολόγηση: ${pending}`;
    }
  };

  const applyConfidence = (card, value) => {
    const cardId = card.dataset.flashcardId;
    if (!cardId || !VALID_STATES.has(value)) return;

    card.dataset.confidence = value;
    card.querySelectorAll('[data-confidence]').forEach((button) => {
      const active = button.dataset.confidence === value;
      button.setAttribute('aria-pressed', String(active));
    });
    state[cardId] = value;
    safeWrite(state);
    updateSummary(card.closest('[data-flashcard-deck]'));
  };

  const toggleCard = (card, forceOpen = null) => {
    const answer = card.querySelector('[data-flashcard-answer]');
    const button = card.querySelector('[data-flashcard-toggle]');
    if (!answer || !button) return;

    const shouldOpen = forceOpen === null ? answer.hidden : forceOpen;
    answer.hidden = !shouldOpen;
    button.setAttribute('aria-expanded', String(shouldOpen));
    button.textContent = shouldOpen ? 'Απόκρυψη απάντησης' : 'Εμφάνιση απάντησης';
    card.classList.toggle('is-open', shouldOpen);
    card.querySelectorAll('[data-confidence]').forEach((control) => {
      control.disabled = !shouldOpen;
    });
  };

  document.querySelectorAll('[data-flashcard-deck]').forEach((deck) => {
    const cards = [...deck.querySelectorAll('[data-flashcard-id]')];

    cards.forEach((card) => {
      const stored = state[card.dataset.flashcardId];
      if (VALID_STATES.has(stored)) {
        card.dataset.confidence = stored;
      }

      card.querySelector('[data-flashcard-toggle]')?.addEventListener('click', () => {
        toggleCard(card);
      });

      card.querySelectorAll('[data-confidence]').forEach((button) => {
        button.addEventListener('click', () => {
          applyConfidence(card, button.dataset.confidence);
        });
      });

      if (VALID_STATES.has(card.dataset.confidence)) {
        card.querySelectorAll('[data-confidence]').forEach((button) => {
          button.setAttribute(
            'aria-pressed',
            String(button.dataset.confidence === card.dataset.confidence)
          );
        });
      }
    });

    deck.querySelector('[data-flashcards-open-all]')?.addEventListener('click', () => {
      cards.forEach((card) => toggleCard(card, true));
    });

    deck.querySelector('[data-flashcards-close-all]')?.addEventListener('click', () => {
      cards.forEach((card) => toggleCard(card, false));
    });

    deck.querySelector('[data-flashcards-reset]')?.addEventListener('click', () => {
      cards.forEach((card) => {
        delete state[card.dataset.flashcardId];
        delete card.dataset.confidence;
        card.querySelectorAll('[data-confidence]').forEach((button) => {
          button.setAttribute('aria-pressed', 'false');
        });
      });
      safeWrite(state);
      updateSummary(deck);
    });

    updateSummary(deck);
  });

  document.querySelectorAll('[data-quiz]').forEach((form) => {
    form.addEventListener('submit', () => {
      queueMicrotask(() => {
        form.querySelectorAll('[data-question-id]').forEach((question) => {
          const feedback = question.querySelector('.question-feedback');
          if (!feedback) return;

          const correct = question.classList.contains('is-correct');
          const detail = correct
            ? question.dataset.feedbackCorrect
            : question.dataset.feedbackIncorrect;
          if (detail) {
            feedback.textContent = correct
              ? `Σωστή απάντηση. ${detail}`
              : `Λανθασμένη απάντηση. ${detail}`;
          }
        });
      });
    });
  });
})();
