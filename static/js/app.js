const fileIn   = document.getElementById('fileIn');
const drop     = document.getElementById('drop');
const dropName = document.getElementById('dropName');
const runBtn   = document.getElementById('runBtn');
const progWrap = document.getElementById('progWrap');
const progFill = document.getElementById('progFill');
const dot      = document.getElementById('dot');
const statusLbl   = document.getElementById('statusLbl');
const statusEmpty = document.getElementById('statusEmpty');
const ttable   = document.getElementById('ttable');
const dlBtn    = document.getElementById('dlBtn');
const histList = document.getElementById('histList');
 
let file = null, fmt = null, taskId = null, poll = null, history = [];
 
// ── format btns ──
document.querySelectorAll('.fmt').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.fmt').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    fmt = b.dataset.f;
    tick();
  });
});
 
// ── file ──
fileIn.addEventListener('change', e => { if (e.target.files[0]) setFile(e.target.files[0]); });
drop.addEventListener('dragover',  e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
 
function setFile(f) {
  file = f;
  dropName.textContent = f.name;
  dropName.style.display = 'block';
  document.getElementById('formatContainer').classList.remove('hidden');
  document.getElementById('statusEmpty').style.display = 'none';
  tick();
}
 
function tick() { runBtn.disabled = !(file && fmt); }
 
// ── run ──
runBtn.addEventListener('click', async () => {
  if (!file || !fmt) return;
  setDot('running', 'загрузка...');
  runBtn.disabled = true;
  progWrap.style.display = 'block';
  progFill.style.background = 'var(--yellow)';
  progFill.style.width = '25%';
  dlBtn.style.display = 'none';
 
  const fd = new FormData();
  fd.append('file', file);
 
  try {
    const r = await fetch(`/tasks/upload?target_format=${fmt}&plan_tier=free`, {
      method: 'POST', body: fd
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'ошибка'); }
    const task = await r.json();
    taskId = task.id;
    progFill.style.width = '55%';
    showTask(task);
    startPoll(task.id);
  } catch(e) {
    setDot('fail', 'ошибка: ' + e.message);
    progFill.style.width = '100%';
    progFill.style.background = 'var(--red)';
    runBtn.disabled = false;
  }
});
 
function startPoll(id) {
  if (poll) clearInterval(poll);
  poll = setInterval(() => doPoll(id), 2000);
}
 
async function doPoll(id) {
  try {
    const r = await fetch(`/tasks/${id}`);
    if (!r.ok) return;
    const t = await r.json();
    showTask(t);
 
    if (t.status === 'completed') {
      clearInterval(poll);
      setDot('done', 'готово');
      progFill.style.width = '100%';
      progFill.style.background = 'var(--green)';
      dlBtn.href = `/download/${id}`;
      dlBtn.style.display = 'inline-block';
      runBtn.disabled = false;
      history.unshift(t);
      renderHistory();
    }
    if (t.status === 'failed') {
      clearInterval(poll);
      setDot('fail', 'ошибка конвертации');
      progFill.style.width = '100%';
      progFill.style.background = 'var(--red)';
      runBtn.disabled = false;
    }
  } catch {}
}
 
function showTask(t) {
  statusEmpty.style.display = 'none';
  ttable.style.display = 'table';
  document.getElementById('tId').textContent     = t.id.slice(0,8) + '…';
  document.getElementById('tFile').textContent   = t.file_name;
  document.getElementById('tFmt').textContent    = t.target_format.toUpperCase();
  document.getElementById('tStatus').textContent = t.status;
  if (t.status === 'in_progress') setDot('running', 'конвертация...');
}
 
function setDot(cls, lbl) {
  dot.className = 'dot ' + cls;
  statusLbl.textContent = lbl;
}
 
function renderHistory() {
  if (!history.length) {
    histList.innerHTML = '<div class="no-hist">задач ещё не было</div>';
    return;
  }
  histList.innerHTML = history.slice(0,12).map(t => `
    <div class="hist-row">
      <span class="hist-name">${t.file_name}</span>
      <span class="hist-fmt">${t.target_format}</span>
      <span class="chip ${t.status}">${t.status}</span>
    </div>`).join('');
}
 
// ── load history ──
(async () => {
  try {
    const r = await fetch('/tasks/');
    if (r.ok) { history = await r.json(); renderHistory(); }
  } catch {}
})();