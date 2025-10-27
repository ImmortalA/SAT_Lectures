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

function renderRWLesson(lesson) {
  console.log('Rendering R&W lesson:', lesson);
  const titleEl = document.getElementById('rw-title');
  const metaEl = document.getElementById('rw-meta');
  const bodyEl = document.getElementById('rw-body');

  // Display the full unit name
  titleEl.textContent = lesson.unit || lesson.title || 'Lesson';
  metaEl.innerHTML = '';
  const metaPills = [
    el('span', { class: 'pill' }, [lesson.section || 'Reading & Writing']),
    el('span', { class: 'pill' }, [lesson.domain || 'Domain']),
    el('span', { class: 'pill' }, [`~${lesson.duration || 0} min`]),
    (lesson.related_skills && lesson.related_skills.length)
      ? el('span', { class: 'pill' }, [`Skills: ${lesson.related_skills.length}`])
      : null
  ].filter(Boolean);
  metaPills.forEach(pill => metaEl.appendChild(pill));

  bodyEl.innerHTML = '';

  const descBlock = lesson.description
    ? el('div', { class: 'content-block' }, [el('div', { class: 'pill' }, ['Description']), el('div', {}, [lesson.description])])
    : null;

  // Render content: handle both markdown and HTML content
  const contentContainer = el('div', { class: 'content-block' });
  contentContainer.appendChild(el('div', { class: 'pill' }, ['Content']));
  
  if (lesson.content) {
    console.log('Rendering R&W content:', lesson.content.substring(0, 100) + '...');
    const contentWrap = el('div', {});
    contentWrap.style.whiteSpace = 'pre-wrap';
    contentWrap.style.lineHeight = '1.5';
    contentWrap.textContent = lesson.content;
    contentContainer.appendChild(contentWrap);
  } else {
    console.log('No content found for R&W lesson:', lesson.id);
    contentContainer.appendChild(el('div', {}, ['No content available']));
  }

  [descBlock, contentContainer].filter(Boolean).forEach(x => bodyEl.appendChild(x));

  localStorage.setItem('rw:last-id', lesson.id || '');
}

async function initRW() {
  const listEl = document.getElementById('rw-list');
  const searchEl = document.getElementById('rw-search');

  // Load new unified lessons schema and filter for R&W only
  const allLessons = await fetchJSON('data/Reading_and_Writing/sat_full_lessons.json').catch(err => {
    console.error('Failed to load R&W lessons:', err);
    return [];
  });
  console.log('Loaded R&W lessons:', allLessons.length);
  const lessons = allLessons.filter(lesson => lesson.section === 'Reading & Writing' || lesson.section === 'Reading and Writing');
  console.log('Filtered R&W lessons:', lessons.length);

  function filterLessons(query) {
    const q = (query || '').toLowerCase();
    if (!q) return lessons;
    return lessons.filter(l => (
      (l.title || '').toLowerCase().includes(q) ||
      (l.unit || '').toLowerCase().includes(q) ||
      (l.domain || '').toLowerCase().includes(q) ||
      (l.section || '').toLowerCase().includes(q) ||
      (l.description || '').toLowerCase().includes(q) ||
      (Array.isArray(l.related_skills) && l.related_skills.some(s => (s || '').toLowerCase().includes(q)))
    ));
  }

  function renderList(filter = '') {
    listEl.innerHTML = '';
    const filteredLessons = filterLessons(filter);
    
    // Group lessons by unit
    const unitGroups = {};
    filteredLessons.forEach(lesson => {
      const unitName = lesson.unit || 'Other';
      if (!unitGroups[unitName]) {
        unitGroups[unitName] = [];
      }
      unitGroups[unitName].push(lesson);
    });
    
    // Render grouped lessons
    Object.entries(unitGroups).forEach(([unitName, unitLessons]) => {
      // Add unit header
      const unitHeader = el('li', { class: 'unit-header' }, [unitName]);
      listEl.appendChild(unitHeader);
      
      // Add lessons under this unit (for R&W, most units have only one lesson)
      unitLessons.forEach(lesson => {
        const lessonTitle = lesson.title || lesson.domain || `Lesson ${lesson.id}`;
        const li = el('li', { class: 'lesson-item' }, [lessonTitle]);
        li.addEventListener('click', () => {
          [...listEl.children].forEach(a => a.classList.remove('active'));
          li.classList.add('active');
          renderRWLesson(lesson);
        });
        listEl.appendChild(li);
      });
    });
  }

  renderList('');
  searchEl.addEventListener('input', e => renderList(e.target.value));

  // Load last viewed or first
  const lastId = localStorage.getItem('rw:last-id');
  const initial = lessons.find(l => l.id === lastId) || lessons[0];
  if (initial) {
    // Mark active in list (look for lesson items, not unit headers)
    const targetLabel = initial.title || initial.domain || `Lesson ${initial.id}`;
    
    [...listEl.children].forEach(li => {
      if (li.classList.contains('lesson-item') && li.textContent === targetLabel) {
        li.classList.add('active');
      }
    });
    renderRWLesson(initial);
  }
}

// ---- Math rendering (uses new flat lesson schema) ----
function renderMathLesson(lesson) {
  console.log('Rendering Math lesson:', lesson);
  const titleEl = document.getElementById('math-title');
  const metaEl = document.getElementById('math-meta');
  const bodyEl = document.getElementById('math-body');

  // Display the full unit name
  titleEl.textContent = lesson.unit || lesson.title || 'Lesson';
  metaEl.innerHTML = '';
  const metaPills = [
    el('span', { class: 'pill' }, [lesson.section || 'Math']),
    el('span', { class: 'pill' }, [lesson.subject || 'Subject']),
    el('span', { class: 'pill' }, [lesson.difficulty || 'Medium']),
    el('span', { class: 'pill' }, [`~${lesson.duration || 0} min`]),
    lesson.category ? el('span', { class: 'pill' }, [lesson.category]) : null
  ].filter(Boolean);
  metaPills.forEach(pill => metaEl.appendChild(pill));

  bodyEl.innerHTML = '';

  const descBlock = lesson.description
    ? el('div', { class: 'content-block' }, [el('div', { class: 'pill' }, ['Description']), el('div', {}, [lesson.description])])
    : null;

  // Render content: handle markdown-style content
  const contentContainer = el('div', { class: 'content-block' });
  contentContainer.appendChild(el('div', { class: 'pill' }, ['Content']));
  
  if (lesson.content) {
    console.log('Rendering Math content:', lesson.content.substring(0, 100) + '...');
    const contentWrap = el('div', {});
    contentWrap.style.whiteSpace = 'pre-wrap';
    contentWrap.style.lineHeight = '1.5';
    contentWrap.textContent = lesson.content;
    contentContainer.appendChild(contentWrap);
  } else {
    console.log('No content found for Math lesson:', lesson.id);
    contentContainer.appendChild(el('div', {}, ['No content available']));
  }

  [descBlock, contentContainer].filter(Boolean).forEach(x => bodyEl.appendChild(x));

  localStorage.setItem('math:last-id', lesson.id || '');
}

async function initMath() {
  const listEl = document.getElementById('math-list');
  const searchEl = document.getElementById('math-search');

  // Load new unified lessons schema and filter for Math only
  const allLessons = await fetchJSON('data/Math/lectures.json').catch(err => {
    console.error('Failed to load Math lessons:', err);
    return [];
  });
  console.log('Loaded Math lessons:', allLessons.length);
  const lessons = allLessons.filter(lesson => lesson.section === 'Math' || !lesson.section);
  console.log('Filtered Math lessons:', lessons.length);

  function filterLessons(query) {
    const q = (query || '').toLowerCase();
    if (!q) return lessons;
    return lessons.filter(l => (
      (l.title || '').toLowerCase().includes(q) ||
      (l.subject || '').toLowerCase().includes(q) ||
      (l.unit || '').toLowerCase().includes(q) ||
      (l.category || '').toLowerCase().includes(q) ||
      (l.description || '').toLowerCase().includes(q)
    ));
  }

  function renderList(filter = '') {
    listEl.innerHTML = '';
    const filteredLessons = filterLessons(filter);
    
    // Group lessons by unit
    const unitGroups = {};
    filteredLessons.forEach(lesson => {
      const unitName = lesson.unit || 'Other';
      if (!unitGroups[unitName]) {
        unitGroups[unitName] = [];
      }
      unitGroups[unitName].push(lesson);
    });
    
    // Render grouped lessons
    Object.entries(unitGroups).forEach(([unitName, unitLessons]) => {
      // Add unit header
      const unitHeader = el('li', { class: 'unit-header' }, [unitName]);
      listEl.appendChild(unitHeader);
      
      // Add lessons under this unit
      unitLessons.forEach(lesson => {
        const lessonTitle = lesson.title || `Lesson ${lesson.id}`;
        const li = el('li', { class: 'lesson-item' }, [lessonTitle]);
        li.addEventListener('click', () => {
          [...listEl.children].forEach(a => a.classList.remove('active'));
          li.classList.add('active');
          renderMathLesson(lesson);
        });
        listEl.appendChild(li);
      });
    });
  }

  renderList('');
  searchEl.addEventListener('input', e => renderList(e.target.value));

  // Load last viewed or first
  const lastId = localStorage.getItem('math:last-id');
  const initial = lessons.find(l => l.id === lastId) || lessons[0];
  if (initial) {
    // Mark active in list (look for lesson items, not unit headers)
    const targetLabel = initial.title || `Lesson ${initial.id}`;
    
    [...listEl.children].forEach(li => {
      if (li.classList.contains('lesson-item') && li.textContent === targetLabel) {
        li.classList.add('active');
      }
    });
    renderMathLesson(initial);
  }
}

// ---- Lectures rendering (uses all_lectures.json) ----
function renderLecture(lecture) {
  console.log('Rendering lecture:', lecture);
  const titleEl = document.getElementById('processed-title');
  const metaEl = document.getElementById('processed-meta');
  const bodyEl = document.getElementById('processed-body');

  titleEl.textContent = lecture.unit || lecture.title || 'Lecture';
  metaEl.innerHTML = '';
  const metaPills = [
    el('span', { class: 'pill' }, [lecture.section || 'Section']),
    el('span', { class: 'pill' }, [lecture.domain || 'Domain']),
    el('span', { class: 'pill' }, [`~${lecture.duration || 0} min`]),
    lecture.related_skills && lecture.related_skills.length > 0 
      ? el('span', { class: 'pill' }, [`${lecture.related_skills.length} skills`])
      : null
  ].filter(Boolean);
  metaPills.forEach(pill => metaEl.appendChild(pill));

  bodyEl.innerHTML = '';

  const descBlock = lecture.description
    ? el('div', { class: 'content-block' }, [
        el('div', { class: 'pill' }, ['Description']), 
        el('div', {}, [lecture.description])
      ])
    : null;

  const skillsBlock = lecture.related_skills && lecture.related_skills.length > 0
    ? el('div', { class: 'content-block' }, [
        el('div', { class: 'pill' }, ['Related Skills']),
        el('div', {}, lecture.related_skills.map(skill => el('span', { class: 'pill', style: 'margin-top: 4px; display: inline-block;' }, [skill])))
      ])
    : null;

  const contentContainer = el('div', { class: 'content-block' });
  contentContainer.appendChild(el('div', { class: 'pill' }, ['Content']));
  
  if (lecture.content) {
    console.log('Rendering lecture content:', lecture.content.substring(0, 100) + '...');
    const contentWrap = el('div', {});
    contentWrap.style.whiteSpace = 'pre-wrap';
    contentWrap.style.lineHeight = '1.5';
    contentWrap.innerHTML = lecture.content;
    contentContainer.appendChild(contentWrap);
  } else {
    contentContainer.appendChild(el('div', {}, ['No content available']));
  }

  const progressBlock = el('div', { class: 'content-block' }, [
    el('div', { class: 'pill' }, ['Progress']),
    el('div', {}, [
      `Progress: ${lecture.progress || 0}%`,
      el('span', { class: 'pill', style: 'margin-left: 8px;' }, [lecture.completed ? 'Completed' : 'In Progress'])
    ])
  ]);

  [descBlock, skillsBlock, contentContainer, progressBlock].filter(Boolean).forEach(x => bodyEl.appendChild(x));

  localStorage.setItem('lectures:last-id', lecture.id || '');
}

async function initLectures() {
  const listEl = document.getElementById('processed-list');
  const searchEl = document.getElementById('processed-search');

  const lectures = await fetchJSON('data/units_processed/all_lectures.json').catch(err => {
    console.error('Failed to load lectures:', err);
    return [];
  });
  console.log('Loaded lectures:', lectures.length);

  function filterLectures(query) {
    const q = (query || '').toLowerCase();
    if (!q) return lectures;
    return lectures.filter(l => (
      (l.unit || '').toLowerCase().includes(q) ||
      (l.section || '').toLowerCase().includes(q) ||
      (l.domain || '').toLowerCase().includes(q) ||
      (l.description || '').toLowerCase().includes(q) ||
      (Array.isArray(l.related_skills) && l.related_skills.some(s => (s || '').toLowerCase().includes(q)))
    ));
  }

  function renderList(filter = '') {
    listEl.innerHTML = '';
    const filteredLectures = filterLectures(filter);
    
    // Group lectures by section and unit
    const groups = {};
    filteredLectures.forEach(lecture => {
      const section = lecture.section || 'Other';
      const unit = lecture.unit || 'Other';
      const key = `${section}::${unit}`;
      if (!groups[key]) {
        groups[key] = { section, unit, lectures: [] };
      }
      groups[key].lectures.push(lecture);
    });
    
    // Sort groups by section, then unit
    const sortedGroups = Object.values(groups).sort((a, b) => {
      if (a.section !== b.section) return a.section.localeCompare(b.section);
      return a.unit.localeCompare(b.unit);
    });
    
    sortedGroups.forEach(group => {
      // Add section/unit header
      const header = el('li', { class: 'unit-header' }, [`${group.section}: ${group.unit}`]);
      listEl.appendChild(header);
      
      // Add lectures under this unit
      group.lectures.forEach(lecture => {
        const li = el('li', { class: 'lesson-item' }, [lecture.unit || 'Lecture']);
        li.addEventListener('click', () => {
          [...listEl.children].forEach(a => a.classList.remove('active'));
          li.classList.add('active');
          renderLecture(lecture);
        });
        listEl.appendChild(li);
      });
    });
  }

  renderList('');
  searchEl.addEventListener('input', e => renderList(e.target.value));

  // Load last viewed or first
  const lastId = localStorage.getItem('lectures:last-id');
  const initial = lectures.find(l => l.id === lastId) || lectures[0];
  if (initial) {
    renderList('');
    // Need to re-render to find the correct item
    setTimeout(() => {
      const targetLabel = initial.unit || 'Lecture';
      [...listEl.children].forEach(li => {
        if (li.classList.contains('lesson-item') && li.textContent === targetLabel) {
          li.classList.add('active');
        }
      });
    }, 0);
    renderLecture(initial);
  }
}

function initTabs() {
  const tabRW = document.getElementById('tab-rw');
  const tabMath = document.getElementById('tab-math');
  const tabProcessed = document.getElementById('tab-processed');
  const tabRubric = document.getElementById('tab-rubric');
  tabRW.addEventListener('click', () => setActive('tab-rw', 'panel-rw'));
  tabMath.addEventListener('click', () => setActive('tab-math', 'panel-math'));
  tabProcessed.addEventListener('click', () => setActive('tab-processed', 'panel-processed'));
  tabRubric.addEventListener('click', () => setActive('tab-rubric', 'panel-rubric'));
}

(async function init() {
  initTabs();
  await Promise.all([initRW(), initMath(), initLectures(), initRubric()]).catch(err => {
    console.error(err);
    document.getElementById('rw-title').textContent = 'Error loading';
    document.getElementById('math-title').textContent = 'Error loading';
    document.getElementById('processed-title').textContent = 'Error loading';
    const rb = document.getElementById('rubric-body');
    if (rb) rb.textContent = 'Error loading rubric';
  });
})();


