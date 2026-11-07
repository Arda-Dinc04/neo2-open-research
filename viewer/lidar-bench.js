'use strict';
const $ = id => document.getElementById(id);
let state = null;
let sending = false;
let shownIndex = -1;
function render(s) {
  state = s;
  $('connection').textContent = s.message;
  const done = s.completed;
  const step = s.steps[Math.min(s.index, s.steps.length - 1)];
  if (shownIndex !== s.index) {
    $('measured').checked = false;
    shownIndex = s.index;
    $('feedback').textContent = '';
  }
  $('step-count').textContent = done ? 'ALL 9 POSITIONS RECORDED' : `POSITION ${s.index + 1} / ${s.total}`;
  $('step-title').textContent = done ? 'Target sequence complete' : step.label;
  $('distance').textContent = done ? 'Saved locally' : step.distance_m === null ? 'No target' : `${step.distance_m.toFixed(1)} m`;
  $('instruction').textContent = done ? 'Open the camera preview and click Disconnect. The Wi-Fi coordinator will restore your usual network. Return to chat for analysis.' : step.distance_m === null ? 'Remove the board from the forward field of view. Keep the background unchanged. No target is not a known distance or an infinite-range measurement.' : 'Place the same upright board directly ahead at the measured distance. Keep its center at the front sensor’s height and keep the background unchanged.';
  $('timer').textContent = s.active ? `${s.active.phase} · ${Math.ceil(s.active.remaining_seconds)} seconds remaining` : done ? 'Next: inspect the captured packets' : s.ready ? 'Position the target, then record' : 'Waiting for live Wi-Fi capture';
  if (s.error) $('feedback').textContent = s.error;
  const width = Number($('width').value), height = Number($('height').value);
  $('record').disabled = !s.ready || !!s.active || done || sending || !$('measured').checked || width < 10 || width > 300 || height < 10 || height > 300;
  $('record').textContent = s.active ? 'Recording local time window…' : done ? 'Sequence saved' : 'Record 5-second hold';
  $('steps').replaceChildren(...s.steps.map((item, i) => {
    const li = document.createElement('li');
    li.textContent = `${i + 1}. ${item.distance_m === null ? 'Clear' : item.distance_m.toFixed(1) + ' m'}`;
    li.className = i < s.index ? 'done' : i === s.index ? 'current' : '';
    return li;
  }));
}
async function poll() {
  try {
    const r = await fetch('/api/state', {cache:'no-store'});
    if (!r.ok) throw Error('Local guide unavailable');
    render(await r.json());
  } catch (_) {
    $('connection').textContent = 'Local guide unavailable';
    $('record').disabled = true;
  } finally { setTimeout(poll, 700); }
}
$('record').addEventListener('click', async () => {
  if (!state || sending) return;
  sending = true; render(state);
  try {
    const r = await fetch('/api/hold', {method:'POST', headers:{'Content-Type':'application/json','X-Bench-Token':state.token}, body:JSON.stringify({measured:$('measured').checked,width_cm:Number($('width').value),height_cm:Number($('height').value)})});
    const result = await r.json();
    if (!r.ok) throw Error(result.error || 'Could not save the hold');
  } catch (e) { $('feedback').textContent = e.message; }
  finally { sending = false; }
});
for (const id of ['measured','width','height']) $(id).addEventListener('input', () => { if (state) render(state); });
poll();
