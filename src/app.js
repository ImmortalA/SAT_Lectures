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

// ---- Utilities ----
function parseCSV(text) {
  const rows = [];
  let i = 0, cur = '', inQuotes = false, field = [], row = [];
  const pushField = () => { row.push(cur); cur = ''; };
  const pushRow = () => { rows.push(row); row = []; };
  while (i < text.length) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cur += '"'; i++; }
        else { inQuotes = false; }
      } else {
        cur += ch;
      }
    } else {
      if (ch === '"') inQuotes = true;
      else if (ch === ',') { pushField(); }
      else if (ch === '\n' || ch === '\r') {
        if (cur.length || row.length) { pushField(); pushRow(); }
        while (text[i + 1] === '\n' || text[i + 1] === '\r') i++;
      } else {
        cur += ch;
      }
    }
    i++;
  }
  if (cur.length || row.length) { pushField(); pushRow(); }
  if (!rows.length) return [];
  const headers = rows[0];
  return rows.slice(1).filter(r => r.length && r.some(x => x && x.trim().length)).map(r => {
    const obj = {};
    headers.forEach((h, idx) => obj[h] = r[idx]);
    return obj;
  });
}

function formatPercent(x) {
  return (Math.round(x * 1000) / 10).toFixed(1) + '%';
}

function byAsc(prop) { return (a, b) => (a[prop] ?? 0) - (b[prop] ?? 0); }

// ---- Rubric rendering ----
async function initRubric() {
  const sectionFilterEl = document.getElementById('rubric-section-filter');
  const body = document.getElementById('rubric-body');
  const meta = document.getElementById('rubric-meta');
  const targetPointsEl = document.getElementById('rubric-target-points');
  const targetWeeksEl = document.getElementById('rubric-target-weeks');
  const applyBtn = document.getElementById('rubric-apply');

  const [spec, csvText, rubricMarkdown] = await Promise.all([
    fetch('data/SAT_Plan_Evaluation/rubric_spec.json').then(r => r.json()),
    fetch('data/SAT_Plan_Evaluation/questions.csv').then(r => r.text()),
    fetch('data/SAT_Plan_Evaluation/rubric.md').then(r => r.text()).catch(() => '')
  ]);

  const rows = parseCSV(csvText).map(x => ({
    id: x.id,
    section: x.section,
    domain: x.domain,
    skill: x.skill,
    difficulty: Number(x.difficulty),
    accuracy: Number(x.accuracy)
  }));

  // threshold removed from UI for simplicity

  function computeDomainAccuracy(sectionFilter = 'all') {
    const acc = new Map();
    rows
      .filter(r => sectionFilter === 'all' ? true : r.section === sectionFilter)
      .forEach(r => {
        const key = `${r.section}|||${r.domain}`;
        const cur = acc.get(key) || { section: r.section, domain: r.domain, correct: 0, total: 0 };
        cur.correct += r.accuracy ? 1 : 0;
        cur.total += 1;
        acc.set(key, cur);
      });
    const list = [...acc.values()].map(x => ({ ...x, accuracy: x.total ? x.correct / x.total : 0 }));
    list.sort((a, b) => a.accuracy - b.accuracy || a.section.localeCompare(b.section));
    return list;
  }

  function generateLessonPlan(domainAccuracies) {
    const maxLessons = spec.parameters?.max_lessons ?? 10;
    const minPerDomain = spec.parameters?.min_questions_per_domain_for_selection ?? 1;
    const quotas = spec.parameters?.practice_quota || { easy: 15, medium: 10, hard: 5 };
    const selected = [];
    domainAccuracies.forEach(item => {
      if (selected.length >= maxLessons) return;
      const totalInDomain = rows.filter(r => r.section === item.section && r.domain === item.domain).length;
      if (totalInDomain >= minPerDomain) selected.push(item);
    });
    return selected.slice(0, maxLessons).map((x, i) => ({
      idx: i + 1,
      section: x.section,
      domain: x.domain,
      accuracy: x.accuracy,
      practice: quotas
    }));
  }

  function estimateLessonPointsGain(section) {
    // Heuristic: base gain per lesson by section; adjust as needed
    return section === 'Math' ? 10 : 8;
  }

  function scheduleLessons(planItems, opts) {
    const { targetPoints = 0, targetWeeks = 0 } = opts || {};
    const lessons = [...planItems];
    // If targets given, cap number of lessons accordingly
    let capByPoints = lessons.length;
    if (targetPoints > 0) {
      let acc = 0, count = 0;
      for (const p of lessons) {
        acc += estimateLessonPointsGain(p.section);
        count++;
        if (acc >= targetPoints) break;
      }
      capByPoints = Math.min(count, lessons.length);
    }
    let capped = lessons.slice(0, capByPoints);

    // Distribute across weeks/days
    const weeks = targetWeeks > 0 ? targetWeeks : Math.ceil(capped.length / 3);
    const perWeek = Math.max(1, Math.ceil(capped.length / weeks));
    const schedule = [];
    let i = 0;
    for (let w = 1; w <= weeks; w++) {
      const weekItems = [];
      for (let d = 1; d <= 7 && i < capped.length && weekItems.length < perWeek; d++) {
        weekItems.push({ day: d, lesson: capped[i++] });
      }
      schedule.push({ week: w, items: weekItems });
      if (i >= capped.length) break;
    }

    return { scheduleWeeks: schedule, totalLessons: capped.length };
  }

  function renderTable(items) {
    const table = el('div', { class: 'table' });
    const header = el('div', { class: 'tr thead' }, [
      el('div', { class: 'th' }, ['Section']),
      el('div', { class: 'th' }, ['Domain']),
      el('div', { class: 'th num' }, ['Correct/Total']),
      el('div', { class: 'th num' }, ['Accuracy'])
    ]);
    table.appendChild(header);
    items.forEach(x => {
      const rowEl = el('div', { class: 'tr' }, [
        el('div', { class: 'td' }, [x.section]),
        el('div', { class: 'td' }, [x.domain]),
        el('div', { class: 'td num' }, [`${x.correct}/${x.total}`]),
        el('div', { class: 'td num' }, [formatPercent(x.accuracy)])
      ]);
      table.appendChild(rowEl);
    });
    return table;
  }

  function renderPlan(items) {
    const wrap = el('div', {});
    items.forEach(x => {
      wrap.appendChild(el('div', { class: 'content-block' }, [
        el('div', { class: 'pill' }, [`Lesson ${x.idx}`]),
        el('div', {}, [el('strong', {}, [`${x.section} — ${x.domain}`]), ' ', el('span', { class: 'pill' }, [`Current: ${formatPercent(x.accuracy)}`])]),
        el('div', {}, [`Practice set: ${x.practice.easy}E / ${x.practice.medium}M / ${x.practice.hard}H`])
      ]));
    });
    return wrap;
  }

  function render(sectionValue, planOverride) {
    const domainAcc = computeDomainAccuracy(sectionValue);
    meta.innerHTML = '';
    meta.append(
      el('span', { class: 'pill' }, [`Domains: ${domainAcc.length}`]),
      el('span', { class: 'pill' }, [`Questions: ${rows.length}`])
    );
    body.innerHTML = '';

    const accBlock = el('div', { class: 'section' }, [
      el('h3', {}, ['Domain accuracy (lowest first)']),
      renderTable(domainAcc)
    ]);

    const quotas = spec.parameters?.practice_quota || { easy: 15, medium: 10, hard: 5 };
    const exitT = spec.parameters?.exit_ticket_count || { easy: 2, medium: 2, hard: 1 };
    const structure = spec.lesson_structure || [];
    const structureBlock = el('div', { class: 'section' }, [
      el('h3', {}, ['Per-unit practice']),' ', el('div', {}, [`Easy ${quotas.easy}, Medium ${quotas.medium}, Hard ${quotas.hard}`])
    ]);

    const plan = planOverride?.planItems || generateLessonPlan(domainAcc);
    const planBlock = el('div', { class: 'section' }, [
      el('h3', {}, ['Auto-generated lesson plan']),
      renderPlan(plan)
    ]);

    // Schedule rendering
    const targetPoints = Number(targetPointsEl?.value || 0);
    const targetWeeks = Number(targetWeeksEl?.value || 0);
    const sched = scheduleLessons(plan, { targetPoints, targetWeeks });
    const schedBlock = el('div', { class: 'section' }, [
      el('h3', {}, ['Schedule (Week / Day)']),
      el('div', { class: 'content-block' }, [
        el('div', {}, [`Target +points: ${targetPoints || 0}, Weeks: ${targetWeeks || Math.ceil(plan.length / 3)}`]),
        el('div', {}, [`Total lessons scheduled: ${sched.totalLessons}`])
      ]),
      el('div', {}, sched.scheduleWeeks.map(w => el('div', { class: 'content-block' }, [
        el('div', { class: 'pill' }, [`Week ${w.week}`]),
        el('ul', {}, w.items.map(it => el('li', {}, [
          `Day ${it.day}: Lesson ${it.lesson.idx} — ${it.lesson.section} / ${it.lesson.domain}`
        ])))
      ])))
    ]);

    const mdBlock = null;

    body.append(accBlock, structureBlock, planBlock, schedBlock, mdBlock);
  }

  sectionFilterEl.addEventListener('change', e => render(e.target.value));
  applyBtn?.addEventListener('click', () => render(sectionFilterEl.value));
  render(sectionFilterEl.value);
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
  const data = await fetchJSON(`data/Reading_and_Writing/${file}`);
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
  const manifest = await fetchJSON('data/Reading_and_Writing/lessons_manifest.json');

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
  const data = await fetchJSON('data/Math/lectures.json').catch(() => ({ units: [] }));
  // Normalize units to match expected keys from possible snake_case schema
  const units = (data.units || []).map(u => {
    const unitTitle = u.unitTitle || u.unit_title || 'Unit';
    const slug = (u.slug || u.unit_id || unitTitle)
      .toString()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    const lectures = (u.lectures || u.structure || []).map(sec => ({
      title: sec.title || 'Lecture',
      contentHtml: sec.contentHtml || (sec.content && sec.content.html) || ''
    }));
    return { ...u, unitTitle, slug, lectures };
  });

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
        const li = el('li', {}, [u.unitTitle || 'Unit']);
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
  const tabRubric = document.getElementById('tab-rubric');
  tabRW.addEventListener('click', () => setActive('tab-rw', 'panel-rw'));
  tabMath.addEventListener('click', () => setActive('tab-math', 'panel-math'));
  tabRubric.addEventListener('click', () => setActive('tab-rubric', 'panel-rubric'));
}

(async function init() {
  initTabs();
  await Promise.all([initRW(), initMath(), initRubric()]).catch(err => {
    console.error(err);
    document.getElementById('rw-title').textContent = 'Error loading';
    document.getElementById('math-title').textContent = 'Error loading';
    const rb = document.getElementById('rubric-body');
    if (rb) rb.textContent = 'Error loading rubric';
  });
})();


