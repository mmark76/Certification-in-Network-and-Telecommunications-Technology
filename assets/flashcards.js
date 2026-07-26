(() => {
  'use strict';

  const STORAGE_KEY = 'ntt-flashcard-confidence-v1';
  const VALID_STATES = new Set(['known', 'review']);
  const FLASHCARD_ID_PATTERN = /^[A-Z][A-Z0-9]{1,7}-[0-9]{3}$/;

  const safeWrite = (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  };

  const safeRemove = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Flashcards remain usable when storage is unavailable.
    }
  };

  const safeRead = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === null) return {};

      const parsed = JSON.parse(stored);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        safeRemove();
        return {};
      }

      const normalized = Object.fromEntries(
        Object.entries(parsed).filter(
          ([cardId, value]) => FLASHCARD_ID_PATTERN.test(cardId) && VALID_STATES.has(value)
        )
      );
      if (JSON.stringify(parsed) !== JSON.stringify(normalized)) {
        safeWrite(normalized);
      }
      return normalized;
    } catch {
      safeRemove();
      return {};
    }
  };

  const state = safeRead();

  const deckCards = (deck) => {
    if (!deck) return [];
    return [...deck.querySelectorAll('[data-flashcard-id]')].filter(
      (card) => card.closest('[data-flashcard-deck]') === deck
    );
  };

  const deckControl = (deck, selector) => {
    if (!deck) return null;
    return [...deck.querySelectorAll(selector)].find(
      (control) => control.closest('[data-flashcard-deck]') === deck
    ) || null;
  };

  const updateSummary = (deck) => {
    if (!deck) return;

    const cards = deckCards(deck);
    const known = cards.filter((card) => card.dataset.confidence === 'known').length;
    const review = cards.filter((card) => card.dataset.confidence === 'review').length;
    const pending = cards.length - known - review;
    const status = deckControl(deck, '[data-flashcard-summary]');
    if (status) {
      status.textContent = `Γνωστές: ${known} · Για επανάληψη: ${review} · Χωρίς αξιολόγηση: ${pending}`;
    }
  };

  const applyConfidence = (card, value) => {
    if (!card) return;

    const cardId = card.dataset.flashcardId;
    const deck = card.closest('[data-flashcard-deck]');
    if (!cardId || !deck || !VALID_STATES.has(value)) return;

    card.dataset.confidence = value;
    card.querySelectorAll('[data-confidence]').forEach((button) => {
      const active = button.dataset.confidence === value;
      button.setAttribute('aria-pressed', String(active));
    });
    state[cardId] = value;
    safeWrite(state);
    updateSummary(deck);
  };

  const toggleCard = (card, forceOpen = null) => {
    if (!card) return false;

    const answer = card.querySelector('[data-flashcard-answer]');
    const button = card.querySelector('[data-flashcard-toggle]');
    if (!answer || !button) {
      card.querySelectorAll('[data-confidence]').forEach((control) => {
        control.disabled = true;
      });
      if (button) button.disabled = true;
      return false;
    }

    const shouldOpen = forceOpen === null ? answer.hidden : forceOpen;
    answer.hidden = !shouldOpen;
    button.setAttribute('aria-expanded', String(shouldOpen));
    button.textContent = shouldOpen ? 'Απόκρυψη απάντησης' : 'Εμφάνιση απάντησης';
    if (card.dataset.flashcardId) {
      button.setAttribute(
        'aria-label',
        `${button.textContent} για την κάρτα ${card.dataset.flashcardId}`
      );
    }
    card.classList.toggle('is-open', shouldOpen);
    card.querySelectorAll('[data-confidence]').forEach((control) => {
      control.disabled = !shouldOpen;
    });
    return true;
  };

  document.querySelectorAll('[data-flashcard-deck]').forEach((deck) => {
    const cards = deckCards(deck);

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

      toggleCard(card, false);
    });

    deckControl(deck, '[data-flashcards-open-all]')?.addEventListener('click', () => {
      cards.forEach((card) => toggleCard(card, true));
    });

    deckControl(deck, '[data-flashcards-close-all]')?.addEventListener('click', () => {
      cards.forEach((card) => toggleCard(card, false));
    });

    deckControl(deck, '[data-flashcards-reset]')?.addEventListener('click', () => {
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
})();
