const fileIn = document.getElementById('fileIn');
const drop = document.getElementById('drop');
const dropName = document.getElementById('dropName');
const runBtn = document.getElementById('runBtn');
const progWrap = document.getElementById('progWrap');
const progFill = document.getElementById('progFill');
const dot = document.getElementById('dot');
const statusLbl = document.getElementById('statusLbl');
const statusEmpty = document.getElementById('statusEmpty');
const formatContainer = document.getElementById('formatContainer');
const formatGroups = document.getElementById('formatGroups');
const statusBlock = document.getElementById('statusBlock');
const ttable = document.getElementById('ttable');
const dlBtn = document.getElementById('dlBtn');
const histList = document.getElementById('histList');

const SIGNATURES = {
  png: bytes => startsWith(bytes, [0x89, 0x50, 0x4e, 0x47]),
  jpg: bytes => startsWith(bytes, [0xff, 0xd8, 0xff]),
  gif: bytes => startsWith(bytes, [0x47, 0x49, 0x46, 0x38]),
  bmp: bytes => startsWith(bytes, [0x42, 0x4d]),
  tiff: bytes => (
    startsWith(bytes, [0x49, 0x49, 0x2a, 0x00]) ||
    startsWith(bytes, [0x4d, 0x4d, 0x00, 0x2a])
  ),
  webp: bytes => matchAscii(bytes, 0, 'RIFF') && matchAscii(bytes, 8, 'WEBP'),
  flac: bytes => matchAscii(bytes, 0, 'fLaC'),
  mp3: bytes => matchAscii(bytes, 0, 'ID3') || hasMp3FrameSync(bytes),
  wav: bytes => matchAscii(bytes, 0, 'RIFF') && matchAscii(bytes, 8, 'WAVE'),
  avi: bytes => matchAscii(bytes, 0, 'RIFF') && matchAscii(bytes, 8, 'AVI '),
  ogg: bytes => matchAscii(bytes, 0, 'OggS'),
  mkv: bytes => startsWith(bytes, [0x1a, 0x45, 0xdf, 0xa3]),
  mp4: bytes => matchAscii(bytes, 4, 'ftyp')
};

let file = null;
let fmt = null;
let taskId = null;
let poll = null;
let tasks = [];
let formatConfig = null;
let fileReadToken = 0;
let expandedTaskId = null;

fileIn.addEventListener('change', e => {
  if (e.target.files[0]) setFile(e.target.files[0]);
});

drop.addEventListener('dragover', e => {
  e.preventDefault();
  drop.classList.add('over');
});

drop.addEventListener('dragleave', () => drop.classList.remove('over'));

drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});

runBtn.addEventListener('click', async () => {
  if (!file || !fmt) return;

  setDot('running', 'загрузка...');
  showStatusBlock();
  runBtn.disabled = true;
  progWrap.classList.remove('hidden');
  progFill.style.background = 'var(--yellow)';
  progFill.style.width = '25%';
  dlBtn.classList.add('hidden');

  const fd = new FormData();
  fd.append('file', file);

  try {
    const response = await fetch(`/tasks/upload?target_format=${fmt}&plan_tier=free`, {
      method: 'POST',
      body: fd
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || 'ошибка');
    }

    taskId = payload.id;
    progFill.style.width = '55%';
    showTask(payload);
    upsertTask(payload);
    expandedTaskId = payload.id;
    renderHistory();
    startPoll(payload.id);
  } catch (error) {
    setDot('fail', `ошибка: ${error.message}`);
    progFill.style.width = '100%';
    progFill.style.background = 'var(--red)';
    runBtn.disabled = false;
  }
});

async function bootstrap() {
  await Promise.all([loadFormats(), loadTasks()]);
}

async function loadFormats() {
  const response = await fetch('/formats/');
  if (!response.ok) {
    throw new Error('Не удалось загрузить список форматов');
  }
  formatConfig = await response.json();
}

async function loadTasks() {
  try {
    const response = await fetch('/tasks/');
    if (!response.ok) return;
    tasks = await response.json();
    expandedTaskId = tasks[0]?.id || null;
    renderHistory();
  } catch {}
}

async function setFile(nextFile) {
  const token = ++fileReadToken;

  file = nextFile;
  fmt = null;
  taskId = null;

  dropName.textContent = nextFile.name;
  dropName.classList.remove('hidden');
  dlBtn.classList.add('hidden');
  progWrap.classList.add('hidden');
  progFill.style.width = '0%';
  statusEmpty.textContent = 'Определяем формат файла...';
  statusEmpty.style.display = 'block';
  formatGroups.innerHTML = '';
  formatContainer.classList.add('hidden');
  tick();

  try {
    const source = await detectFile(nextFile);
    if (token === fileReadToken) renderFormats(source);
  } catch {
    if (token !== fileReadToken) return;
    statusEmpty.textContent = 'Не удалось прочитать файл';
  }

  tick();
}

async function detectFile(selectedFile) {
  const extension = getExtension(selectedFile.name);
  const header = await readHeader(selectedFile);

  return (
    detectBySignature(header, extension, selectedFile.type) ||
    detectByMime(selectedFile.type, extension) ||
    detectByExtension(extension) ||
    { extension, group: null }
  );
}

async function readHeader(selectedFile) {
  const buffer = await selectedFile.slice(0, 65536).arrayBuffer();
  return new Uint8Array(buffer);
}

function detectBySignature(bytes, extension, mime) {
  if (SIGNATURES.png(bytes)) return source('image', 'png');
  if (SIGNATURES.jpg(bytes)) return source('image', 'jpg');
  if (SIGNATURES.gif(bytes)) return source('image', 'gif');
  if (SIGNATURES.bmp(bytes)) return source('image', 'bmp');
  if (SIGNATURES.tiff(bytes)) return source('image', 'tiff');
  if (SIGNATURES.webp(bytes)) return source('image', 'webp');
  if (SIGNATURES.flac(bytes)) return source('audio', 'flac');
  if (SIGNATURES.mp3(bytes)) return source('audio', 'mp3');
  if (SIGNATURES.wav(bytes)) return source('audio', 'wav');
  if (SIGNATURES.avi(bytes)) return source('video', 'avi');
  if (SIGNATURES.ogg(bytes)) {
    return source(mime.startsWith('video/') || extension === 'ogv' ? 'video' : 'audio', extension || 'ogg');
  }
  if (SIGNATURES.mkv(bytes)) {
    return source(extension === 'mka' ? 'audio' : 'video', extension || 'mkv');
  }
  if (SIGNATURES.mp4(bytes)) {
    const group = mime.startsWith('audio/') || extension === 'm4a' ? 'audio' : 'video';
    return source(group, extension || (group === 'audio' ? 'm4a' : 'mp4'));
  }
  return null;
}

function detectByMime(mime, extension) {
  if (!mime) return null;
  if (mime.startsWith('video/')) return source('video', extension);
  if (mime.startsWith('audio/')) return source('audio', extension);
  if (mime.startsWith('image/')) return source('image', extension);
  if (['application/x-subrip', 'text/vtt'].includes(mime)) {
    return source('subtitle', extension);
  }
  return null;
}

function detectByExtension(extension) {
  if (!formatConfig) return null;
  return Object.entries(formatConfig.groups).find(([, group]) =>
    group.inputs.includes(extension)
  )?.[0]
    ? source(
        Object.entries(formatConfig.groups).find(([, group]) =>
          group.inputs.includes(extension)
        )[0],
        extension
      )
    : null;
}

function source(group, extension) {
  return { group, extension: normalizeExtension(extension) };
}

function startsWith(bytes, signature) {
  return signature.every((byte, index) => bytes[index] === byte);
}

function matchAscii(bytes, offset, text) {
  return [...text].every((char, index) => bytes[offset + index] === char.charCodeAt(0));
}

function hasMp3FrameSync(bytes) {
  return bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0;
}

function renderFormats(sourceInfo) {
  formatGroups.innerHTML = '';
  formatContainer.classList.add('hidden');
  statusEmpty.style.display = 'block';

  if (!sourceInfo.group || !formatConfig) {
    statusEmpty.textContent = sourceInfo.extension
      ? `Формат .${sourceInfo.extension} пока не поддерживается`
      : 'Не удалось определить формат файла';
    return;
  }

  const groups = getOutputGroups(sourceInfo);
  if (!groups.length) {
    statusEmpty.textContent = `Для .${sourceInfo.extension} нет доступных форматов`;
    return;
  }

  statusEmpty.style.display = 'none';
  formatContainer.classList.remove('hidden');
  groups.forEach(renderFormatGroup);
}

function getExtension(name) {
  const parts = name.toLowerCase().split('.');
  return normalizeExtension(parts.length > 1 ? parts.pop() : '');
}

function normalizeExtension(extension) {
  if (!formatConfig) return extension;
  return formatConfig.aliases[extension] || extension;
}

function getOutputGroups(sourceInfo) {
  return formatConfig.output_groups[sourceInfo.group]
    .map(name => ({
      name,
      label: formatConfig.groups[name].label,
      formats: formatConfig.groups[name].outputs.filter(output => output !== sourceInfo.extension)
    }))
    .filter(group => group.formats.length);
}

function renderFormatGroup(group) {
  const wrapper = document.createElement('div');
  const title = document.createElement('p');
  const list = document.createElement('div');

  title.className = 'text-xs font-bold tracking-[0.1em] text-zinc-400 uppercase mb-2';
  title.textContent = group.label;
  list.className = 'flex flex-wrap gap-2';

  group.formats.forEach(format => {
    const button = document.createElement('button');
    button.className = 'fmt px-3 py-2 text-xs border border-border rounded hover:border-accent hover:text-accent transition';
    button.dataset.f = format;
    button.type = 'button';
    button.textContent = format.toUpperCase();
    button.addEventListener('click', () => selectFormat(button, format));
    list.appendChild(button);
  });

  wrapper.append(title, list);
  formatGroups.appendChild(wrapper);
}

function selectFormat(button, format) {
  document.querySelectorAll('.fmt').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  fmt = format;
  tick();
}

function tick() {
  runBtn.disabled = !(file && fmt);
}

function startPoll(id) {
  if (poll) clearInterval(poll);
  poll = setInterval(() => doPoll(id), 2000);
}

async function doPoll(id) {
  try {
    const response = await fetch(`/tasks/${id}`);
    if (!response.ok) return;

    const task = await response.json();
    showTask(task);
    upsertTask(task);
    renderHistory();

    if (task.status === 'completed') {
      clearInterval(poll);
      setDot('done', 'готово');
      progFill.style.width = '100%';
      progFill.style.background = 'var(--green)';
      dlBtn.href = `/download/${id}`;
      dlBtn.classList.remove('hidden');
      runBtn.disabled = false;
      return;
    }

    if (task.status === 'failed' || task.status === 'expired') {
      clearInterval(poll);
      setDot('fail', task.status === 'expired' ? 'файл удалён' : 'ошибка конвертации');
      progFill.style.width = '100%';
      progFill.style.background = 'var(--red)';
      runBtn.disabled = false;
    }
  } catch {}
}

function showTask(task) {
  showStatusBlock();
  statusEmpty.style.display = 'none';
  ttable.classList.remove('hidden');
  document.getElementById('tId').textContent = `${task.id.slice(0, 8)}...`;
  document.getElementById('tFile').textContent = task.file_name;
  document.getElementById('tFmt').textContent = task.target_format.toUpperCase();
  document.getElementById('tStatus').textContent = statusLabel(task.status);
  dlBtn.classList.toggle('hidden', task.status !== 'completed');

  if (task.status === 'in_progress') setDot('running', 'конвертация...');
}

function showStatusBlock() {
  statusBlock.classList.remove('hidden');
}

function setDot(cls, lbl) {
  dot.className = `dot ${cls}`;
  statusLbl.textContent = lbl;
}

function upsertTask(task) {
  const index = tasks.findIndex(item => item.id === task.id);
  if (index === -1) {
    tasks.unshift(task);
  } else {
    tasks[index] = task;
  }

  tasks.sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

function renderHistory() {
  if (!tasks.length) {
    histList.innerHTML = '<div class="no-hist">задач ещё не было</div>';
    return;
  }

  histList.innerHTML = tasks.slice(0, 12).map(renderHistoryTask).join('');
  histList.querySelectorAll('[data-task-toggle]').forEach(button => {
    button.addEventListener('click', () => toggleTask(button.dataset.taskToggle));
  });
}

function downloadIconSvg() {
  return `<svg class="hist-download-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M12 3v10"/>
    <path d="m8 9 4 4 4-4"/>
    <path d="M5 21h14"/>
  </svg>`;
}

function renderHistoryTask(task) {
  const expanded = expandedTaskId === task.id;
  const canDownload = task.status === 'completed';
  const expiredAt = task.expires_at ? formatDate(task.expires_at) : '—';
  const error = task.error_message ? escapeHtml(task.error_message) : '—';

  return `
    <div class="hist-item ${expanded ? 'open' : ''}">
      <div class="hist-row">
        <button class="hist-toggle" type="button" data-task-toggle="${task.id}">
          <span class="hist-name">${escapeHtml(task.file_name)}</span>
          <span class="hist-fmt">${escapeHtml(task.target_format)}</span>
          <span class="chip ${escapeHtml(task.status)}">${statusLabel(task.status)}</span>
        </button>
        ${canDownload ? `
          <a class="hist-download" href="/download/${task.id}" download title="Скачать" aria-label="Скачать">
            ${downloadIconSvg()}
          </a>
        ` : '<span class="hist-download hist-download-empty"></span>'}
      </div>
      <div class="hist-detail ${expanded ? '' : 'hidden'}">
        <div class="hist-meta">
          <span>ID: ${escapeHtml(task.id.slice(0, 8))}...</span>
          <span>Статус: ${statusLabel(task.status)}</span>
          <span>Удаление: ${escapeHtml(expiredAt)}</span>
        </div>
        <div class="hist-error ${task.error_message ? '' : 'hidden'}">${error}</div>
      </div>
    </div>
  `;
}

function toggleTask(nextId) {
  expandedTaskId = expandedTaskId === nextId ? null : nextId;
  renderHistory();
}

function statusLabel(status) {
  if (status === 'pending') return 'в очереди';
  if (status === 'in_progress') return 'идёт';
  if (status === 'completed') return 'готово';
  if (status === 'failed') return 'ошибка';
  if (status === 'expired') return 'удалено';
  return status;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return '—';
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

bootstrap().catch(() => {
  statusEmpty.textContent = 'Не удалось загрузить конфигурацию конвертера';
});
