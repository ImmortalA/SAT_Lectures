async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}`);
  return res.json();
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'class') node.className = v; else if (k === 'html') node.innerHTML = v; else node.setAttribute(k, v);
  });
  (children || []).forEach(c => node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
  return node;
}

function renderLesson(lesson) {
  const titleEl = document.getElementById('title');
  const metaEl = document.getElementById('meta');
  const bodyEl = document.getElementById('body');

  titleEl.textContent = lesson.unit || lesson.title || 'Processed Unit';
  metaEl.innerHTML = '';
  const pills = [
    el('span', { class: 'pill' }, [lesson.section || 'Math']),
    el('span', { class: 'pill' }, [lesson.domain || 'Domain']),
    el('span', { class: 'pill' }, [`~${lesson.duration || 0} min`])
  ].filter(Boolean);
  pills.forEach(p => metaEl.appendChild(p));

  bodyEl.innerHTML = '';
  const descBlock = lesson.description
    ? el('div', { class: 'content-block' }, [el('div', { class: 'pill' }, ['Description']), el('div', {}, [lesson.description])])
    : null;

  const contentContainer = el('div', { class: 'content-block' });
  contentContainer.appendChild(el('div', { class: 'pill' }, ['Content']));
  if (lesson.content) {
    const contentWrap = el('div', {});
    contentWrap.innerHTML = lesson.content; // HTML/MathML
    contentContainer.appendChild(contentWrap);
  } else {
    contentContainer.appendChild(el('div', {}, ['No content available']));
  }

  [descBlock, contentContainer].filter(Boolean).forEach(x => bodyEl.appendChild(x));
  localStorage.setItem('processed:last-id', lesson.id || '');
}

async function init() {
  const listEl = document.getElementById('list');
  const searchEl = document.getElementById('search');
  const filePicker = document.getElementById('file-picker');

  // Prefer a manifest; else try known grouped files
  let lessons = await fetchJSON('../data/units_processed/manifest.json').catch(() => [])
    .then(arr => Array.isArray(arr) ? arr : []);

  if (!lessons.length) {
    const files = [
      'unit-01-exponents-radicals.grouped.json','unit-02-percent.grouped.json','unit-03-manipulating-solving-equations.grouped.json','unit-04-rates.grouped.json','unit-05-expressions.grouped.json','unit-06-manipulating-solving-equations.grouped.json','unit-07-more-equation-solving-strategies.grouped.json','unit-08-systems-of-equations.grouped.json','unit-09-inequalities.grouped.json','unit-10-word-problems.grouped.json','unit-11-lines.grouped.json','unit-12-interpreting-linear-models.grouped.json','unit-13-functions.grouped.json','unit-14-quadratics.grouped.json','unit-15-synthetic-division.grouped.json','unit-16-mixed-practice-test-strategies.grouped.json','unit-17-absolute-value.grouped.json','unit-18-angles.grouped.json','unit-19-triangles.grouped.json','unit-20-circles.grouped.json','unit-21-trigonometry.grouped.json','unit-22-reading-data.grouped.json','unit-23-probability.grouped.json','unit-24-statistics-i.grouped.json','unit-25-statistics-ii.grouped.json','unit-26-volume.grouped.json'
    ];
    const fetched = await Promise.all(files.map(name => fetchJSON(`../data/units_processed/${name}`).catch(() => null)));
    lessons = fetched.filter(Boolean);
  }

  function filterLessons(query) {
    const q = (query || '').toLowerCase();
    if (!q) return lessons;
    return lessons.filter(l => (
      (l.unit || '').toLowerCase().includes(q) ||
      (l.domain || '').toLowerCase().includes(q) ||
      (l.section || '').toLowerCase().includes(q) ||
      (l.description || '').toLowerCase().includes(q)
    ));
  }

  function renderList(filter = '') {
    listEl.innerHTML = '';
    if (!lessons.length) {
      listEl.appendChild(el('li', { class: 'unit-header' }, ['No processed units found.']));
      return;
    }
    const filtered = filterLessons(filter);
    const groups = {};
    filtered.forEach(l => {
      const unitName = l.unit || 'Other';
      if (!groups[unitName]) groups[unitName] = [];
      groups[unitName].push(l);
    });
    Object.entries(groups).forEach(([unitName, unitLessons]) => {
      listEl.appendChild(el('li', { class: 'unit-header' }, [unitName]));
      unitLessons.forEach(lesson => {
        const label = lesson.title || lesson.unit || lesson.domain || `Unit ${lesson.id || ''}`;
        const li = el('li', { class: 'lesson-item' }, [label]);
        li.addEventListener('click', () => {
          [...listEl.children].forEach(a => a.classList.remove('active'));
          li.classList.add('active');
          renderLesson(lesson);
        });
        listEl.appendChild(li);
      });
    });
  }

  renderList('');
  searchEl.addEventListener('input', e => renderList(e.target.value));

  // Allow manual selection of JSON files if server path differs
  filePicker.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const loaded = await Promise.all(files.map(f => f.text().then(JSON.parse).catch(() => null)));
    const valid = loaded.filter(Boolean);
    if (valid.length) {
      lessons = valid;
      renderList(searchEl.value || '');
    }
  });

  const lastId = localStorage.getItem('processed:last-id');
  const initial = lessons.find(l => l.id === lastId) || lessons[0];
  if (initial) {
    const targetLabel = initial.title || initial.unit || initial.domain || `Unit ${initial.id || ''}`;
    [...listEl.children].forEach(li => {
      if (li.classList.contains('lesson-item') && li.textContent === targetLabel) li.classList.add('active');
    });
    renderLesson(initial);
  }
}

init();


