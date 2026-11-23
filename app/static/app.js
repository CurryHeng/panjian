const $ = id => document.getElementById(id);
let project = null, clips = [], dirty = false, busy = false, timer = null, pollTimer = null;
const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const time = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${(seconds % 60).toFixed(1).padStart(4, '0')}`;
function notice(message, error = false) {
  $('notice').textContent = message; $('notice').classList.toggle('error', error);
  $('notice').style.display = 'block'; clearTimeout(timer);
  timer = setTimeout(() => $('notice').style.display = 'none', 6000);
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = '操作失败，请稍后重试';
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : '参数无效，请检查输入');
  }
  return response.json();
}
function status() {
  $('save-state').textContent = !project ? '尚未选择素材' : dirty ? '有未保存修改' : '片段已保存至本机';
  $('save').disabled = !project || busy;
  $('export').disabled = !clips.length || busy;
  $('add').disabled = !project || busy;
  $('projects').disabled = busy;
  $('file').disabled = busy;
  document.querySelectorAll('.clip input, .clip textarea, .clip button, #start, #end, #mark-start, #mark-end').forEach(control => { control.disabled = busy; });
  document.querySelectorAll('.clip').forEach((card, i) => {
    const clip = clips[i], next = clips[i+1];
    const hasTail = validRange(clip.start, clip.end) && clip.end < project.duration;
    for (const name of ['tail','extend']) card.querySelector(`[data-action=${name}]`).disabled = busy || !hasTail;
    card.querySelector('[data-action=merge]').disabled = busy || !canMerge(clip, next);
    card.querySelector('[data-action=up]').disabled = busy || i === 0;
    card.querySelector('[data-action=down]').disabled = busy || i === clips.length-1;
  });
}
function renderTimeline() {
  const d = project ? project.duration : 0;
  $('tl-track').innerHTML = d ? clips.filter(c => validRange(c.start, c.end)).map(c => {
    const i = clips.indexOf(c);
    return `<span class="tl-clip" style="left:${c.start / d * 100}%;width:${(c.end - c.start) / d * 100}%" title="${escapeHtml(c.title)}">${String(i + 1).padStart(2, '0')}</span>`;
  }).join('') : '';
  movePlayhead();
}
function movePlayhead() {
  const d = project ? project.duration : 0;
  $('tl-head').style.left = d ? `${Math.min(100, $('video').currentTime / d * 100)}%` : '0';
}
function render() {
  renderTimeline();
  $('count').textContent = clips.length;
  $('total').textContent = `共 ${clips.reduce((sum, c) => sum + Math.max(0, c.end - c.start), 0).toFixed(1)} 秒`;
  $('clips').innerHTML = clips.length ? clips.map((c, i) => `<article class="clip" data-index="${i}">
    <div class="clip-head"><span class="clip-index">${String(i + 1).padStart(2, '0')}</span><input data-key="title" aria-label="片段标题" maxlength="200" placeholder="给这个回合起个名字" value="${escapeHtml(c.title)}"></div>
    <div class="clip-times"><input data-key="start" aria-label="片段开始秒数" type="number" min="0" step="0.1" value="${c.start}"><span>→</span><input data-key="end" aria-label="片段结束秒数" type="number" min="0" step="0.1" value="${c.end}"><span>秒</span></div>
    <textarea data-key="notes" aria-label="片段备注" maxlength="4000" placeholder="记录配合亮点或待确认的细节">${escapeHtml(c.notes)}</textarea>
    <div class="clip-actions"><button data-action="tail">预览后两秒</button><button data-action="extend">延长两秒</button><button data-action="merge" title="仅合并相接或重叠的两个片段">合并下一段</button></div>
    <div class="clip-actions"><button data-action="preview">预览</button><button data-action="up">↑</button><button data-action="down">↓</button><button class="delete" data-action="delete">移除</button></div></article>`).join('') : '<div class="empty-list">还没有选中回合<br><small>在左侧标记起止时间，添加第一个片段。</small></div>';
  status();
}
async function refreshProjects(selected) {
  const projects = await api('/api/projects');
  $('projects').innerHTML = projects.length ? projects.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('') : '<option value="">还没有素材，请先导入视频</option>';
  if (selected) $('projects').value = selected;
  return projects;
}
function validRange(start, end) {
  return project && Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end > start && end <= project.duration;
}
function canMerge(a, b) {
  return b && validRange(a.start,a.end) && validRange(b.start,b.end)
    && Math.max(a.start,b.start) <= Math.min(a.end,b.end);
}
async function openProject(id) {
  if (!id) return;
  busy = true; status();
  try {
  clearTimeout(pollTimer);
  project = await api(`/api/projects/${id}`); clips = project.clips; dirty = false;
  $('video').src = `/api/projects/${id}/source`; $('empty').hidden = true;
  $('source-name').textContent = project.name;
  $('metadata').textContent = `${time(project.duration)} · ${project.width} × ${project.height} · ${(project.bytes / 1024 / 1024).toFixed(1)} MB`;
  $('start').value = 0; $('end').value = Math.min(10, project.duration).toFixed(1);
  previewEnd = null;
  $('start').max = $('end').max = project.duration;
  $('job').textContent = ''; $('downloads').replaceChildren(); $('result').removeAttribute('src'); $('result').hidden = true; render();
  localStorage.setItem('panjian-project', id);
  const jobs = await api(`/api/projects/${id}/exports`);
  jobs.filter(j => j.status === 'completed').forEach(addDownload);
  const pending = jobs.find(j => ['queued', 'running'].includes(j.status));
  busy = false;
  if (pending) { busy = true; monitor(pending.id); }
  else if (jobs.length && !jobs.some(j=>j.status==='completed')) $('job').textContent = jobs[jobs.length-1].error || '';
  } catch (error) { busy = false; throw error; }
  finally { status(); }
}
function safeDownloadName() {
  let name = ($('download-name').value || '').trim().replace(/[\\/:*?"<>|]/g, '_');
  if (!name) name = 'panjian-highlight';
  if (!/\.mp4$/i.test(name)) name += '.mp4';
  $('download-name').value = name;
  return name;
}

async function chooseLocation(job) {
  const name = safeDownloadName();
  if (!window.showSaveFilePicker) {
    const link = document.createElement('a'); link.href = job.download_url; link.download = name; link.click();
    notice('当前浏览器不支持选择位置，已使用默认下载位置'); return;
  }
  try {
    const handle = await window.showSaveFilePicker({suggestedName: name, types: [{description: 'MP4 视频', accept: {'video/mp4': ['.mp4']}}]});
    const response = await fetch(job.download_url); if (!response.ok) throw new Error('下载文件失败');
    const writable = await handle.createWritable(); await writable.write(await response.blob()); await writable.close();
    notice('视频已保存到选择的位置');
  } catch (error) {
    if (error.name !== 'AbortError') notice(error.message || '保存失败，请重试', true);
  }
}

$('download-name').addEventListener('blur', safeDownloadName);

function addDownload(job) {
  if (document.getElementById(`download-${job.id}`)) return;
  const a = document.createElement('a'); a.id = `download-${job.id}`;
  a.href = job.download_url; a.download = safeDownloadName(); a.textContent = '↓ 下载已生成的精彩集锦';
  a.addEventListener('click', () => { a.download = safeDownloadName(); });
  $('downloads').prepend(a);
  $('download-options').hidden = false;
  $('choose-location').onclick = () => chooseLocation(job);
  $('result').hidden = false; $('result').src = job.download_url;
}
async function save() {
  if (clips.some(c => !validRange(c.start, c.end))) throw new Error('请检查每个片段：0 ≤ 开始 < 结束 ≤ 视频时长');
  project = await api(`/api/projects/${project.id}/clips`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({clips})});
  dirty = false; status();
}
async function monitor(id) {
  try {
    const job = await api(`/api/jobs/${id}`);
    $('job').textContent = {queued:'等待处理…',running: job.stage==='analyzing'?'正在分析比赛画面并选择回合…':'正在生成高清集锦…',completed:'集锦已生成，可以播放或下载。',failed:job.error,no_candidates:job.error}[job.status];
    if (job.status === 'completed') addDownload(job);
    if (['completed', 'failed','no_candidates'].includes(job.status)) {
      if (job.automatic && job.status==='completed') {
        project = await api(`/api/projects/${job.project_id}`); clips = project.clips; render();
      }
      busy = false; status(); return;
    }
    pollTimer = setTimeout(() => monitor(id), 1500);
  } catch (error) { busy = false; status(); notice(error.message, true); }
}
$('file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  if (dirty && !confirm('当前片段有未保存修改，仍要导入其他素材吗？')) { event.target.value = ''; return; }
  if (file.size > 2 * 1024 ** 3) { notice('单个视频不能超过 2 GiB', true); return; }
  busy = true; status(); notice('正在导入并读取视频，请稍候…');
  const form = new FormData(); form.append('file', file);
  try { const p = await api('/api/projects?auto=true', {method:'POST', body:form}); await refreshProjects(p.id); await openProject(p.id); notice('视频已导入，集锦将自动生成'); }
  catch (error) { busy = false; notice(error.message, true); }
  finally { status(); event.target.value = ''; }
});
$('projects').addEventListener('change', async event => {
  if (dirty && !confirm('当前有未保存修改，仍要切换吗？')) { event.target.value = project.id; return; }
  try { await openProject(event.target.value); } catch (e) { notice(e.message, true); }
});
$('mark-start').onclick = () => $('start').value = $('video').currentTime.toFixed(2);
$('mark-end').onclick = () => $('end').value = $('video').currentTime.toFixed(2);
$('add').onclick = () => {
  const start = Number($('start').value), end = Number($('end').value);
  if (!validRange(start, end)) return notice('请设置有效起止时间：开始需早于结束，并且不能超出素材时长', true);
  if (clips.length >= 100) return notice('首版最多支持 100 个片段', true);
  clips.push({id:crypto.randomUUID(), start, end, title:`精彩回合 ${clips.length + 1}`, notes:''}); dirty = true; render();
};
$('clips').addEventListener('input', event => {
  const key = event.target.dataset.key; if (!key) return;
  const index = Number(event.target.closest('.clip').dataset.index);
  clips[index][key] = ['start','end'].includes(key) ? Number(event.target.value) : event.target.value;
  dirty = true; $('total').textContent = `共 ${clips.reduce((s,c) => s + Math.max(0,c.end-c.start),0).toFixed(1)} 秒`; renderTimeline(); status();
});
$('timeline').addEventListener('click', event => {
  if (!project) return;
  const box = $('timeline').getBoundingClientRect();
  $('video').currentTime = Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)) * project.duration;
});
let previewEnd = null;
$('clips').addEventListener('click', event => {
  const action = event.target.dataset.action; if (!action) return;
  const i = Number(event.target.closest('.clip').dataset.index);
  const clip = clips[i];
  const tailEnd = Math.min(clip.end + 2, project.duration);
  if (action === 'preview' || action === 'tail') {
    if (!validRange(clips[i].start, clips[i].end)) return notice('请先修正片段时间', true);
    $('video').currentTime = action === 'tail' ? clip.end : clip.start;
    previewEnd = action === 'tail' ? tailEnd : clip.end;
    $('video').play().catch(e => notice(`播放器无法播放该格式：${e.message}`, true)); return;
  }
  if (action === 'extend') clip.end = tailEnd;
  if (action === 'merge') {
    const next = clips[i+1];
    if (!canMerge(clip, next)) return;
    const title = [...new Set([clip.title,next.title].filter(Boolean))].join(' / ');
    const notes = [clip.notes,next.notes].filter(Boolean).join('\n');
    if (title.length > 200 || notes.length > 4000) return notice('合并后标题或备注过长，请先精简再合并', true);
    Object.assign(clip,{start:Math.min(clip.start,next.start),end:Math.max(clip.end,next.end),title,notes});
    clips.splice(i+1,1);
  }
  if (action === 'delete') clips.splice(i, 1);
  if (action === 'up' && i > 0) [clips[i-1],clips[i]] = [clips[i],clips[i-1]];
  if (action === 'down' && i < clips.length-1) [clips[i+1],clips[i]] = [clips[i],clips[i+1]];
  dirty = true; render();
});
$('video').addEventListener('timeupdate', () => {
  $('playhead').textContent = time($('video').currentTime); movePlayhead();
  if (previewEnd !== null && $('video').currentTime >= previewEnd) { $('video').pause(); previewEnd = null; }
});
$('video').addEventListener('error', () => notice('浏览器不能预览该视频编码。建议使用 H.264 编码的 MP4；服务端导出仍可能可用。', true));
$('save').onclick = async () => {
  busy = true; status();
  try { await save(); notice('片段已保存'); }
  catch (e) { notice(e.message, true); }
  finally { busy = false; status(); }
};
$('export').onclick = async () => {
  busy = true; status();
  try { await save(); const job = await api(`/api/projects/${project.id}/exports`, {method:'POST'}); await monitor(job.id); }
  catch (e) { busy = false; status(); notice(e.message, true); }
};
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
(async () => {
  try {
    const projects = await refreshProjects();
    const remembered = localStorage.getItem('panjian-project');
    const chosen = projects.find(p => p.id === remembered) || projects[0];
    if (chosen) { $('projects').value = chosen.id; await openProject(chosen.id); }
  } catch (e) { notice(e.message, true); }
})();
