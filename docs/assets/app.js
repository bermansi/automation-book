(function () {
  const state = {
    section: null
  };

  function allExercises() {
    return window.BOOK_DATA.exercises || [];
  }

  function availableSections() {
    return [...new Set(allExercises().map(e => e.section))];
  }

  function defaultSection() {
    return availableSections()[0] || 'all';
  }

  function sectionTitle(id) {
    for (const chapter of window.BOOK_DATA.chapters) {
      for (const section of chapter.sections || []) {
        if (section.id === id) return `${section.id} ${section.title}`;
      }
    }
    return id;
  }

  function chapterForSection(sectionId) {
    for (const chapter of window.BOOK_DATA.chapters) {
      for (const section of chapter.sections || []) {
        if (section.id === sectionId) return chapter;
      }
    }
    return null;
  }

  function sectionFromHash() {
    const hash = decodeURIComponent(window.location.hash || '');
    if (!hash) return null;
    const sectionMatch = hash.match(/^#section-(\d+)-(\d+)$/);
    if (sectionMatch) return `${sectionMatch[1]}.${sectionMatch[2]}`;
    const exerciseMatch = hash.match(/^#ex-(.+)$/);
    if (exerciseMatch) {
      const ex = allExercises().find(item => item.id === exerciseMatch[1]);
      if (ex) return ex.section;
    }
    return null;
  }

  function setCurrentSection(sectionId, options = {}) {
    const available = availableSections();
    if (!sectionId || !available.includes(sectionId)) {
      sectionId = defaultSection();
    }
    state.section = sectionId;
    const select = document.getElementById('section-filter');
    if (select) select.value = sectionId;
    renderNav();
    renderExercises(sectionId);
    if (options.updateHash) {
      const hash = `#section-${sectionId.replaceAll('.', '-')}`;
      if (window.location.protocol === 'file:') {
        // The Windows preview opens docs/index.html directly from disk.
        window.location.hash = hash;
      } else {
        history.pushState(null, '', hash);
      }
    }
  }

  function renderNav() {
    const nav = document.getElementById('book-nav');
    nav.innerHTML = '';
    const activeSection = state.section || defaultSection();
    const activeChapter = chapterForSection(activeSection);

    for (const chapter of window.BOOK_DATA.chapters) {
      const chapterDetails = document.createElement('details');
      chapterDetails.className = 'nav-chapter';
      if (activeChapter && chapter.id === activeChapter.id) chapterDetails.open = true;

      const chapterSummary = document.createElement('summary');
      chapterSummary.className = 'nav-chapter-title';
      chapterSummary.textContent = `פרק ${chapter.number} ${chapter.title}`;
      chapterDetails.appendChild(chapterSummary);

      const chapterContent = document.createElement('div');
      chapterContent.className = 'nav-chapter-content';

      for (const section of chapter.sections || []) {
        const sectionExercises = allExercises().filter(e => e.section === section.id);
        const hasExercises = sectionExercises.length > 0;
        const isActive = section.id === activeSection;

        if (!hasExercises) {
          continue;
        }

        const sectionDetails = document.createElement('details');
        sectionDetails.className = 'nav-section-detail';
        if (isActive) sectionDetails.open = true;

        const sectionSummary = document.createElement('summary');
        sectionSummary.className = isActive ? 'nav-section active' : 'nav-section';
        sectionSummary.dataset.section = section.id;
        sectionSummary.textContent = `${section.id} ${section.title}`;
        sectionDetails.appendChild(sectionSummary);

        const exWrap = document.createElement('div');
        exWrap.className = 'nav-exercise-list';
        if (isActive) {
          for (const ex of sectionExercises) {
            const a = document.createElement('a');
            a.className = 'nav-exercise';
            a.href = `#ex-${ex.id}`;
            a.textContent = `${ex.number} ${ex.title}`;
            exWrap.appendChild(a);
          }
        }
        sectionDetails.appendChild(exWrap);
        chapterContent.appendChild(sectionDetails);
      }

      chapterDetails.appendChild(chapterContent);
      nav.appendChild(chapterDetails);
    }
  }

  function renderFilter() {
    const select = document.getElementById('section-filter');
    const sections = availableSections();
    select.innerHTML = sections.map(id => `<option value="${id}">${sectionTitle(id)}</option>`).join('');
    select.addEventListener('change', () => setCurrentSection(select.value, { updateHash: true }));
  }

  function renderExerciseBody(ex) {
    if (Array.isArray(ex.parts) && ex.parts.length) {
      const partsHtml = ex.parts.map(part => `
        <section class="exercise-part">
          <h5>סעיף ${part.label}${part.title ? ' · ' + part.title : ''}</h5>
          <div class="question-label">שאלה</div>
          <div class="question-body">${part.questionHtml}</div>
          <details class="solution">
            <summary>הצג פתרון סעיף ${part.label}</summary>
            <div class="solution-body">${part.solutionHtml}</div>
          </details>
        </section>
      `).join('');
      return `
        <div class="question-label">מבנה השאלה</div>
        <div class="question-body">${ex.questionHtml || ''}</div>
        <div class="parts-list">${partsHtml}</div>
      `;
    }
    return `
      <div class="question-label">שאלה</div>
      <div class="question-body">${ex.questionHtml}</div>
      <details class="solution">
        <summary>הצג פתרון</summary>
        <div class="solution-body">${ex.solutionHtml}</div>
      </details>
    `;
  }

  function fixBidiFragments(root) {
    // Keep variable tokens with subscripts/superscripts together in one LTR unit.
    root.querySelectorAll('.ltr-inline').forEach(span => {
      span.setAttribute('dir', 'ltr');
      span.style.direction = 'ltr';
      span.style.unicodeBidi = 'isolate-override';
      while (span.nextSibling && span.nextSibling.nodeType === 1 && ['SUB', 'SUP'].includes(span.nextSibling.nodeName)) {
        span.appendChild(span.nextSibling);
      }
    });
  }

  function renderExercises(sectionId = state.section || defaultSection()) {
    const list = document.getElementById('exercise-list');
    const chapterTitle = document.getElementById('chapter-title');
    const title = document.getElementById('content-title');
    const intro = document.getElementById('content-intro');
    list.innerHTML = '';

    const exercises = allExercises().filter(e => e.section === sectionId);
    const chapter = chapterForSection(sectionId);
    chapterTitle.textContent = chapter ? `פרק ${chapter.number} ${chapter.title}` : '';
    title.textContent = sectionTitle(sectionId);
    intro.textContent = 'מוצגות כאן רק השאלות של הסעיף הנבחר. אפשר לעבור לסעיפים אחרים דרך התפריט הצדדי או דרך הסינון.';

    const marker = document.createElement('div');
    marker.id = `section-${sectionId.replaceAll('.', '-')}`;
    marker.className = 'section-marker';
    marker.setAttribute('aria-hidden', 'true');
    list.appendChild(marker);

    for (const ex of exercises) {
      const article = document.createElement('article');
      article.className = 'exercise-card';
      article.id = `ex-${ex.id}`;
      article.innerHTML = `
        <div class="exercise-meta"><span>שאלה ${ex.number}</span><span>·</span><span>${sectionTitle(ex.section)}</span></div>
        <h4 class="exercise-title">${ex.number} ${ex.title}</h4>
        ${renderExerciseBody(ex)}
      `;
      list.appendChild(article);
    }

    fixBidiFragments(list);
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise([list]).catch(() => {});
    }
  }

  function setupMenu() {
    const button = document.getElementById('menu-button');
    button.addEventListener('click', () => document.body.classList.toggle('sidebar-open'));
    document.getElementById('book-nav').addEventListener('click', event => {
      const sectionSummary = event.target.closest('summary.nav-section');
      if (sectionSummary && sectionSummary.dataset.section) {
        event.preventDefault();
        setCurrentSection(sectionSummary.dataset.section, { updateHash: true });
        if (window.matchMedia('(max-width: 900px)').matches) document.body.classList.remove('sidebar-open');
        return;
      }
      if (event.target.closest('a.nav-exercise')) {
        if (window.matchMedia('(max-width: 900px)').matches) document.body.classList.remove('sidebar-open');
      }
    });
  }

  window.addEventListener('hashchange', () => {
    const section = sectionFromHash();
    if (section && section !== state.section) setCurrentSection(section);
  });

  document.addEventListener('DOMContentLoaded', () => {
    renderFilter();
    setCurrentSection(sectionFromHash() || defaultSection());
    setupMenu();
  });
}());
