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

function setActive(tabId, panelId) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.getElementById(tabId).classList.add('active');
  document.getElementById(panelId).classList.remove('hidden');
}

// ---- Reading & Writing rendering (reuses existing RW schema) ----
function renderRWQAItem(item) {
  const opts = Object.entries(item.options || {}).map(([k, v]) => el('div', {}, [`${k}. ${v}`]));
  return el('div', { class: 'qa content-block' }, [
    el('div', { class: 'q' }, [item.question || 'Question']),
    ...opts,
    item.correct_answer ? el('div', { class: 'pill' }, [`Answer: ${item.correct_answer}`]) : null
  ].filter(Boolean));
}

function renderRWLectureScript(arr) {
  return el('div', {}, (arr || []).map(step => el('div', { class: 'script-item' }, [
    el('span', { class: 'pill' }, [step.type]),
    el('span', {}, [`${step.duration_min} min - `, step.script])
  ])));
}

function renderRWWorkedExample(we) {
  return el('div', { class: 'content-block' }, [
    el('div', { class: 'pill' }, ['Worked Example']),
    el('div', {}, [we.passage || '']),
    renderRWQAItem(we)
  ]);
}

function renderRWPracticeSet(arr) {
  return el('div', { class: 'grid-2' }, (arr || []).map(renderRWQAItem));
}

function renderRWSection(section) {
  return el('div', { class: 'section' }, [
    el('h3', {}, [section.title || 'Section']),
    el('div', { class: 'meta' }, [el('span', { class: 'pill' }, [`~${section.time_suggested_minutes || 0} min`])]),
    el('div', {}, [el('strong', {}, ['Objectives'])]),
    el('ul', { class: 'objectives' }, (section.objectives || []).map(o => el('li', {}, [o]))),
    el('div', {}, [el('strong', {}, ['Lecture Script'])]),
    renderRWLectureScript(section.lecture_script || []),
    el('div', {}, [el('strong', {}, ['Content'])]),
    section.content?.worked_example ? renderRWWorkedExample(section.content.worked_example) : null,
    section.content?.practice_set ? renderRWPracticeSet(section.content.practice_set) : null
  ].filter(Boolean));
}

async function loadRWLesson(file, manifest) {
  const data = await fetchJSON(`Reading_and_Writing/${file}`);
  document.getElementById('rw-title').textContent = data.unit_title || 'Lesson';
  const meta = document.getElementById('rw-meta');
  meta.innerHTML = '';
  meta.append(
    el('span', { class: 'pill' }, [data.target_exam || 'SAT R&W']),
    el('span', { class: 'pill' }, [`Mastery: ${data.total_mastery_points || 0}`])
  );
  const body = document.getElementById('rw-body');
  body.innerHTML = '';

  const notes = el('div', { class: 'content-block' }, [
    el('div', { class: 'pill' }, ['Teacher Notes']),
    el('div', {}, [`Pacing: ${data.teacher_notes?.pacing || ''}`]),
    el('div', {}, [`Materials: ${data.teacher_notes?.materials || ''}`]),
    el('div', {}, [`Assessment: ${data.teacher_notes?.assessment || ''}`])
  ]);
  const lo = el('div', { class: 'content-block' }, [
    el('div', { class: 'pill' }, ['Learning Objectives']),
    el('ul', {}, (data.learning_objectives || []).map(x => el('li', {}, [x])))
  ]);
  body.append(notes, lo);

  (data.structure || []).forEach(sec => body.appendChild(renderRWSection(sec)));
  if (data.unit_check) body.appendChild(el('div', {}, [el('h3', {}, ['Unit Check']), el('div', { class: 'grid-2' }, data.unit_check.map(renderRWQAItem))]));
  if (data.homework) body.appendChild(el('div', {}, [el('h3', {}, ['Homework']), el('ul', {}, data.homework.map(x => el('li', {}, [x])))]));

  localStorage.setItem('rw:last', file);
}

async function initRW() {
  const listEl = document.getElementById('rw-list');
  const searchEl = document.getElementById('rw-search');
  const manifest = await fetchJSON('Reading_and_Writing/lessons_manifest.json');

  function renderList(filter = '') {
    listEl.innerHTML = '';
    manifest
      .filter(x => x.label.toLowerCase().includes(filter.toLowerCase()))
      .forEach((item) => {
        const li = el('li', {}, [item.label]);
        li.addEventListener('click', () => {
          [...listEl.children].forEach(a => a.classList.remove('active'));
          li.classList.add('active');
          loadRWLesson(item.file, manifest).catch(err => console.error(err));
        });
        listEl.appendChild(li);
      });
  }

  renderList('');
  searchEl.addEventListener('input', e => renderList(e.target.value));

  const last = localStorage.getItem('rw:last');
  const first = manifest[0]?.file;
  const toLoad = last || first;
  if (toLoad) await loadRWLesson(toLoad, manifest);
}

// ---- Math rendering (reads prebuilt HTML unit pages via lectures.json) ----
async function initMath() {
  const listEl = document.getElementById('math-list');
  const searchEl = document.getElementById('math-search');
  const data = await fetchJSON('Math/lectures.json').catch(() => ({ units: [] }));
  const units = data.units || [];

  function renderUnit(u) {
    const body = document.getElementById('math-body');
    const title = document.getElementById('math-title');
    const meta = document.getElementById('math-meta');
    title.textContent = u.unitTitle || 'Unit';
    meta.innerHTML = '';
    body.innerHTML = '';

    (u.lectures || []).forEach(lec => {
      body.appendChild(el('div', { class: 'section' }, [
        el('h3', {}, [lec.title || 'Lecture']),
        el('div', { class: 'content-block', html: lec.contentHtml || '' })
      ]));
    });
  }

  function renderList(filter = '') {
    listEl.innerHTML = '';
    units
      .filter(u => (u.unitTitle || '').toLowerCase().includes(filter.toLowerCase()))
      .forEach(u => {
        const li = el('li', {}, [u.unitTitle]);
        li.addEventListener('click', () => {
          [...listEl.children].forEach(a => a.classList.remove('active'));
          li.classList.add('active');
          renderUnit(u);
          localStorage.setItem('math:last', u.slug);
        });
        listEl.appendChild(li);
      });
  }

  renderList('');
  searchEl.addEventListener('input', e => renderList(e.target.value));

  // Load last or first
  const lastSlug = localStorage.getItem('math:last');
  const chosen = units.find(u => u.slug === lastSlug) || units[0];
  if (chosen) renderUnit(chosen);
}

function initTabs() {
  const tabRW = document.getElementById('tab-rw');
  const tabMath = document.getElementById('tab-math');
  tabRW.addEventListener('click', () => setActive('tab-rw', 'panel-rw'));
  tabMath.addEventListener('click', () => setActive('tab-math', 'panel-math'));
}

(async function init() {
  initTabs();
  await Promise.all([initRW(), initMath()]).catch(err => {
    console.error(err);
    document.getElementById('rw-title').textContent = 'Error loading';
    document.getElementById('math-title').textContent = 'Error loading';
  });
})();


