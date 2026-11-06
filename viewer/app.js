'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const palette = { ink: '#172c32', muted: '#85958a', grid: '#dfe5da', a: '#26838b', b: '#c37040', c: '#77689e', lime: '#d5e87b' };
  const ids = ['aircraft', 'gimbal'];
  const staleAfter = 500;
  let state = null;
  let lastReceived = 0;
  let serviceFailed = false;
  let activeTrace = 'aircraft';
  let guideIndex = 0;
  let markerPending = false;
  let lastMarkerSignature = '';
  let guideSession = null;
  let guideNeedsRestart = false;
  let guideRestartedLocally = false;
  const zeros = { aircraft: null, gimbal: null };
  const history = { aircraft: [], gimbal: [] };
  const seen = { aircraft: null, gimbal: null };
  const steps = [
    { label: 'Stationary baseline', axis: 'baseline', degrees: null, title: 'Stationary baseline', detail: 'Place the aircraft level and hold it still for at least three seconds. Wait for both readings to settle, then record a baseline.', action: 'Record stationary baseline' },
    { label: 'Whole-body clockwise yaw +90°', axis: 'yaw', degrees: 90, title: 'Turn the whole aircraft clockwise.', detail: 'Viewed from above, gently rotate the entire aircraft about 90° clockwise. Keep it level and hold still for at least three seconds before recording. Observe which fields change; their signs are not yet certified.', action: 'Record yaw comparison' },
    { label: 'Yaw return baseline', axis: 'baseline', degrees: null, title: 'Return to the starting heading.', detail: 'Return the whole aircraft to its original level position. Hold it still for at least three seconds and let the readings settle before recording a new baseline.', action: 'Record return baseline' },
    { label: 'Whole-body nose up +15°', axis: 'pitch', degrees: 15, title: 'Lift the nose approximately 15°.', detail: 'Gently tilt the entire aircraft nose-up by a small, known angle. Keep the motors idle. Do not touch or force the stabilizing gimbal. Hold still for at least three seconds before recording.', action: 'Record pitch comparison' },
    { label: 'Pitch return baseline', axis: 'baseline', degrees: null, title: 'Return the aircraft to level.', detail: 'Return to the same stationary baseline and heading. Hold still for at least three seconds and allow the gimbal to settle on its own before recording.', action: 'Record return baseline' },
    { label: 'Whole-body right side down +15°', axis: 'roll', degrees: 15, title: 'Lower the right side approximately 15°.', detail: 'Gently tilt the whole aircraft so its right side is lower. Keep motors idle and cable slack. Hold a small known angle still for at least three seconds before recording; compare body fields with the stabilized gimbal.', action: 'Record roll comparison' },
    { label: 'Bench guide finished', axis: 'end', degrees: null, title: 'Return to level and review.', detail: 'Return the aircraft to a stable level position and hold still for at least three seconds. These observations identify candidate axes; this guide does not automatically certify physical signs, scale, or reference frames.', action: 'Finish this comparison' }
  ];

  const number = (v, precision = 1) => typeof v === 'number' && Number.isFinite(v) ? (Math.abs(v) < 0.05 ? 0 : v).toFixed(precision) : '—';
  const validAngles = (c) => c && Array.isArray(c.angles_deg) && c.angles_deg.length === 3 && c.angles_deg.every(Number.isFinite);
  const wrap = (angle) => ((angle + 180) % 360 + 360) % 360 - 180;
  const elapsed = () => lastReceived ? performance.now() - lastReceived : Infinity;
  const age = (c) => c && typeof c.age_ms === 'number' && Number.isFinite(c.age_ms) ? Math.max(0, c.age_ms + elapsed()) : Infinity;
  const fresh = (c) => validAngles(c) && age(c) <= staleAfter && !serviceFailed && !['error', 'disconnected', 'starting'].includes(state?.status);
  const displayAngles = (id) => validAngles(state?.[id]) ? state[id].angles_deg.map((v, i) => zeros[id] ? wrap(v - zeros[id][i]) : v) : [0, 0, 0];
  const sourceString = (source) => {
    if (!source) return 'Awaiting decoded source metadata';
    const toHex = (value) => typeof value === 'number' ? value.toString(16).padStart(2, '0') : String(value ?? '—');
    return `${toHex(source.sender)} → ${toHex(source.receiver)} · ${source.command ?? '—'} · seq ${source.sequence ?? '—'}`;
  };

  function updateStatus() {
    const mode = state?.mode ?? 'waiting';
    const transport = state?.transport ?? {};
    const failed = serviceFailed || ['error', 'disconnected'].includes(state?.status);
    const isStale = !failed && state && (!ids.some((id) => fresh(state[id])) || state.status === 'stale');
    const effective = failed ? 'error' : isStale ? 'stale' : mode;
    const badge = $('mode-badge');
    badge.className = `mode-badge mode-${mode}`;
    badge.textContent = { live: 'LIVE USB / READ ONLY', demo: 'SIMULATED / NO HARDWARE', replay: 'CAPTURE REPLAY / NOT LIVE' }[mode] ?? 'WAITING FOR SOURCE';
    $('connection-dot').className = `status-dot ${failed || isStale ? 'alert' : state?.status === 'streaming' ? 'active' : ''}`;
    $('connection-label').textContent = serviceFailed ? 'Local service unavailable' : { starting: 'Waiting for receive stream', streaming: 'Receiving orientation frames', stale: 'Received data is stale', disconnected: 'USB source disconnected', error: 'Receive path needs attention' }[state?.status] ?? 'Connecting to local viewer';
    $('connection-detail').textContent = failed ? 'Last values are frozen; they are not current.' : mode === 'replay' ? 'Saved values use replay time, not a live sensor clock.' : mode === 'demo' ? 'Generated angles demonstrate the instruments only.' : 'Sample age is measured at this Mac.';
    const notice = $('source-notice');
    notice.className = `notice notice-${effective}`;
    $('source-notice-text').textContent = serviceFailed ? 'The viewer cannot reach its local service. Last received values are frozen. Check the viewer terminal and USB connection.'
      : failed ? `The receive source is unavailable. ${transport.last_error || 'No fresh aircraft or gimbal readings are being received.'}`
      : mode === 'demo' ? 'SIMULATION — generated angles only. No USB hardware is being read. Bench validation is disabled in this mode.'
      : mode === 'replay' ? 'REPLAY — values come from a saved capture, not the connected aircraft. Bench validation is disabled in this mode.'
      : isStale ? 'STALE DATA — the instruments show the last received values. Wait for fresh data before a bench comparison.'
      : state?.status === 'streaming' ? 'LIVE RECEIVE ONLY — orientation frames are arriving over USB. No flight, firmware, or configuration commands are available in this viewer.'
      : 'Waiting for the local receive-only service. Values remain unavailable until data arrives.';
    document.body.classList.toggle('offline', Boolean(failed || isStale));
    $('transport-endpoint').textContent = `${transport.interface ?? 4} / ${transport.endpoint_in ?? '0x85'} IN`;
    $('transport-frames').textContent = typeof transport.frames_total === 'number' ? Math.max(0, transport.frames_total).toLocaleString() : '0';
    $('transport-rate').textContent = Number.isFinite(transport.packet_rate_hz) ? `${number(transport.packet_rate_hz)} Hz` : '— Hz';
    const sampleAge = Number.isFinite(state?.age_ms) ? Math.max(0, state.age_ms + elapsed()) : Infinity;
    $('transport-age').textContent = Number.isFinite(sampleAge) ? sampleAge < 1000 ? `${Math.round(sampleAge)} ms` : `${number(sampleAge / 1000)} s` : '—';
    $('transport-discarded').textContent = Number.isFinite(transport.crc_discarded) ? transport.crc_discarded.toLocaleString() : '0';
    $('gimbal-norm').textContent = number(state?.gimbal?.quaternion_norm, 6);
    $('transport-error').hidden = !transport.last_error;
    $('transport-error').textContent = transport.last_error || '';
    $('service-uptime').textContent = Number.isFinite(state?.uptime_s) ? `SERVICE ${Math.floor(state.uptime_s / 60)}:${String(Math.floor(state.uptime_s % 60)).padStart(2, '0')}` : 'LOCAL SERVICE';
  }

  function updateComponents() {
    for (const id of ids) {
      const component = state?.[id];
      const available = validAngles(component);
      const current = fresh(component);
      $(id + '-panel').classList.toggle('is-unavailable', !current);
      const freshness = $(id + '-freshness');
      freshness.className = `freshness ${current ? 'fresh' : available ? 'stale' : ''}`;
      freshness.textContent = current ? 'FRESH' : available ? 'STALE' : 'NO DATA';
      const angles = displayAngles(id);
      ['a', 'b', 'c'].forEach((axis, index) => { $(id + '-' + axis).textContent = available ? number(angles[index]) : '—'; });
      $(id + '-source').textContent = component ? sourceString(component.source) : id === 'aircraft' ? '03 → 0a · 03/43 · awaiting frames' : '04 → 2a · 04/05 · awaiting frames';
      $(id + '-zero').disabled = !current;
      $(id + '-zero-label').textContent = zeros[id] ? 'LOCAL VIEW ZERO APPLIED' : 'ABSOLUTE FIELDS';
      const sequence = component?.source?.sequence;
      const key = available ? `${sequence ?? ''}/${component.angles_deg.join(',')}/${component.age_ms ?? ''}` : null;
      // Freshness age is not an event ID. When a sequence exists, use it so
      // polling faster than USB updates does not invent extra samples.
      const frameKey = available ? sequence !== undefined ? String(sequence) : key : null;
      if (current && frameKey !== seen[id]) {
        seen[id] = frameKey;
        history[id].push({ time: performance.now(), angles: [...component.angles_deg] });
      }
      const earliest = performance.now() - 31000;
      while (history[id].length && history[id][0].time < earliest) history[id].shift();
    }
    $('reset-zero').disabled = !zeros.aircraft && !zeros.gimbal;
  }

  function updateBench() {
    const markers = Array.isArray(state?.bench?.markers) ? state.bench.markers : [];
    const session = state?.bench?.session_id ?? null;
    if (session !== guideSession) {
      guideSession = session; guideIndex = 0; guideNeedsRestart = false;
      guideRestartedLocally = false; lastMarkerSignature = '';
    }
    const signature = JSON.stringify(markers);
    if (signature !== lastMarkerSignature) {
      if (!guideRestartedLocally) {
        // Resume only this guide's named, ordered sequence. A marker count
        // alone could belong to another browser or a different experiment.
        let progress = null;
        for (const marker of markers) {
          if (marker.label === steps[0].label) progress = 1;
          else if (progress !== null && progress < steps.length && marker.label === steps[progress].label) progress += 1;
        }
        guideNeedsRestart = markers.length > 0 && progress === null;
        if (progress !== null) {
          guideIndex = progress;
          $('bench-feedback').classList.remove('error');
          $('bench-feedback').textContent = `Guide synchronized with the session’s existing annotations (${progress} of ${steps.length} steps). These observations are not automatic axis verification.`;
        } else if (guideNeedsRestart) {
          $('bench-feedback').classList.remove('error');
          $('bench-feedback').textContent = 'This session contains annotations from a different comparison. Review them, then choose Restart guide to explicitly begin this sequence.';
        }
      }
      lastMarkerSignature = signature;
      renderMarkers(markers);
    }
    const canRecord = state?.mode === 'live' && ids.every((id) => fresh(state[id])) && Boolean(state?.api_token);
    const complete = guideIndex >= steps.length;
    const step = steps[Math.min(guideIndex, steps.length - 1)];
    $('bench-step-number').textContent = complete ? '07 / 07 · RECORDED' : `${String(guideIndex + 1).padStart(2, '0')} / 07`;
    $('bench-step-title').textContent = complete ? 'Comparisons recorded.' : step.title;
    $('bench-step-detail').textContent = complete ? 'Review the saved deltas and your reference angles. Candidate axes still require consistent direction, scale, and return-to-baseline checks. Recorded annotations do not automatically mark an axis as verified.' : step.detail;
    $('bench-record').replaceChildren(document.createTextNode(markerPending ? 'Recording annotation…' : complete ? 'Guide complete' : step.action));
    const plus = document.createElement('span'); plus.textContent = complete ? '✓' : '+'; plus.setAttribute('aria-hidden', 'true'); $('bench-record').append(plus);
    $('bench-record').disabled = !canRecord || markerPending || complete || guideNeedsRestart;
    $('bench-gate').className = `bench-gate ${canRecord ? 'ready' : ''}`;
    $('bench-gate').textContent = canRecord ? 'FRESH LIVE DATA / ANNOTATION ONLY' : state?.mode === 'demo' || state?.mode === 'replay' ? 'BENCH VALIDATION DISABLED' : 'FRESH LIVE DATA REQUIRED';
    const track = $('bench-step-track');
    if (!track.children.length) for (let index = 0; index < steps.length; index++) track.append(document.createElement('span'));
    [...track.children].forEach((node, index) => { node.className = index < guideIndex ? 'done' : index === guideIndex ? 'current' : ''; });
    $('bench-session').textContent = state?.bench?.session_id ? `SESSION / ${state.bench.session_id}` : 'NO BENCH SESSION YET';
  }

  function renderMarkers(markers) {
    const list = $('bench-markers'); list.replaceChildren();
    if (!markers.length) {
      const item = document.createElement('li'); item.className = 'empty-marker'; item.textContent = 'No markers recorded. Begin with a stationary baseline.'; list.append(item); return;
    }
    markers.slice(-10).reverse().forEach((marker, index) => {
      const item = document.createElement('li');
      const line = document.createElement('div'); line.className = 'marker-line';
      const title = document.createElement('span'); title.className = 'marker-title';
      const count = document.createElement('span'); count.className = 'marker-number'; count.textContent = String(markers.length - index).padStart(2, '0') + ' '; title.append(count, document.createTextNode(marker.label || 'Bench annotation'));
      const time = document.createElement('span'); time.className = 'marker-time';
      const date = marker.created_at ? new Date(marker.created_at) : null;
      time.textContent = date && !Number.isNaN(date.getTime()) ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
      line.append(title, time); item.append(line);
      for (const [key, label] of [['aircraft_delta', 'Aircraft Δ'], ['gimbal_delta', 'Gimbal Δ']]) {
        if (Array.isArray(marker[key]) && marker[key].length === 3) {
          const detail = document.createElement('p'); detail.className = 'marker-detail'; detail.textContent = `${label} ${marker[key].map((v) => number(v)).join(' / ')}°`; item.append(detail);
        }
      }
      list.append(item);
    });
    let exportLink = $('bench-export');
    if (!exportLink) {
      exportLink = document.createElement('a'); exportLink.id = 'bench-export'; exportLink.className = 'text-button'; exportLink.textContent = 'Export local annotations ↗'; exportLink.href = '/api/bench/export.json'; exportLink.setAttribute('download', 'neo-bench-session.json'); exportLink.style.color = '#d5e87b'; exportLink.style.display = 'inline-block'; exportLink.style.marginTop = '14px'; list.parentElement.append(exportLink);
    }
  }

  async function recordMarker() {
    if (markerPending || guideNeedsRestart || guideIndex >= steps.length || state?.mode !== 'live' || !ids.every((id) => fresh(state[id]))) return;
    markerPending = true; updateBench();
    const step = steps[guideIndex];
    try {
      const response = await fetch('/api/bench/marker', { method: 'POST', credentials: 'same-origin', redirect: 'error', headers: { 'Content-Type': 'application/json', 'X-Viewer-Token': state.api_token }, body: JSON.stringify({ label: step.label, expected_axis: step.axis, expected_degrees: step.degrees }) });
      let result = null;
      try { result = await response.json(); } catch (_) { /* Fall back to a useful local message below. */ }
      if (!response.ok) throw new Error(typeof result?.error === 'string' ? result.error : 'The service did not accept this annotation. Fresh, stable live readings are required.');
      if (!result || typeof result !== 'object') throw new Error('The service returned an invalid annotation response.');
      if (result.ok === false) throw new Error(result.error || 'The annotation was not recorded.');
      if (result.bench && state) state.bench = result.bench;
      guideRestartedLocally = false;
      guideIndex += 1;
      $('bench-feedback').classList.remove('error');
      $('bench-feedback').textContent = 'Observation annotated on this Mac. No command was sent to the aircraft.';
    } catch (error) {
      $('bench-feedback').classList.add('error'); $('bench-feedback').textContent = error.message || 'Unable to record this annotation.';
    } finally { markerPending = false; updateBench(); }
  }

  function canvasContext(id) {
    const canvas = $(id);
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, rect.width), h = Math.max(1, rect.height);
    if (canvas.width !== Math.round(w * ratio) || canvas.height !== Math.round(h * ratio)) {
      canvas.width = Math.round(w * ratio); canvas.height = Math.round(h * ratio);
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  }

  function transformed(point, angles) {
    const [r, p, y] = angles.map((a) => a * Math.PI / 180);
    let [x, yy, z] = point;
    [yy, z] = [yy * Math.cos(r) - z * Math.sin(r), yy * Math.sin(r) + z * Math.cos(r)];
    [x, z] = [x * Math.cos(p) + z * Math.sin(p), -x * Math.sin(p) + z * Math.cos(p)];
    return [x * Math.cos(y) - yy * Math.sin(y), x * Math.sin(y) + yy * Math.cos(y), z];
  }

  function drawInstrument(id) {
    const { ctx, w, h } = canvasContext(id + '-canvas');
    const scale = Math.min(w / 330, h / 205) * (id === 'gimbal' ? 1.1 : 1);
    const cx = w / 2, cy = h / 2 - 3;
    const angles = displayAngles(id);
    // Aircraft drawing coordinates are nose +X, right +Y, up +Z. One bench
    // cycle supports A=pitch, B=roll, C=yaw: positive A raised the nose and
    // positive B lowered the right side. The renderer's right-handed formulas
    // need negative pitch/roll for those illustrative directions. Raw readings
    // and scale remain unchanged. Gimbal uses provisional SDK field order.
    const modelAngles = id === 'aircraft' ? [-angles[1], -angles[0], angles[2]] : [angles[1], angles[0], angles[2]];
    const project = (point, rotated = true) => {
      // The drawn aircraft shape was authored nose −Y / right +X. Normalize
      // geometry before applying candidate body rotations; the fixed floor
      // grid remains in world coordinates.
      const bodyPoint = rotated && id === 'aircraft' ? [-point[1], point[0], point[2]] : point;
      const [x, y, z] = rotated ? transformed(bodyPoint, modelAngles) : bodyPoint;
      return [cx + (x * .88 - y * .4) * scale, cy + (x * .25 + y * .52 - z * .88) * scale];
    };
    const path = (points, stroke, fill = null, lineWidth = 1) => {
      ctx.beginPath(); points.forEach((p, index) => { const [x, y] = p; if (index) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
      if (fill) { ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
      if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lineWidth; ctx.stroke(); }
    };
    ctx.strokeStyle = palette.grid; ctx.lineWidth = .7;
    for (let n = -3; n <= 3; n++) {
      path([project([n * 32, -96, -23], false), project([n * 32, 96, -23], false)], palette.grid);
      path([project([-96, n * 32, -23], false), project([96, n * 32, -23], false)], palette.grid);
    }
    ctx.beginPath(); ctx.ellipse(cx, cy + 14 * scale, 112 * scale, 47 * scale, 0, 0, Math.PI * 2); ctx.strokeStyle = '#c8d2c3'; ctx.setLineDash([2, 5]); ctx.stroke(); ctx.setLineDash([]);
    for (let deg = 0; deg < 360; deg += 30) {
      const a = deg * Math.PI / 180;
      const x = cx + Math.cos(a) * 112 * scale, y = cy + 14 * scale + Math.sin(a) * 47 * scale;
      path([[x, y], [cx + Math.cos(a) * 117 * scale, cy + 14 * scale + Math.sin(a) * 50 * scale]], '#b6c3b0', null, .8);
    }
    if (id === 'aircraft') {
      const motors = [[-55, -43, 0], [55, -43, 0], [-55, 43, 0], [55, 43, 0]];
      for (const motor of motors) path([project([0, 0, 0]), project(motor)], '#849a90', null, 5 * scale);
      for (const motor of motors) {
        const ring = Array.from({ length: 33 }, (_, i) => project([motor[0] + 26 * Math.cos(i * Math.PI / 16), motor[1] + 26 * Math.sin(i * Math.PI / 16), motor[2]]));
        path(ring, '#aebfad', '#eef1e9', 1.4 * scale);
        const inner = Array.from({ length: 25 }, (_, i) => project([motor[0] + 20 * Math.cos(i * Math.PI / 12), motor[1] + 20 * Math.sin(i * Math.PI / 12), motor[2] + 1]));
        path(inner, '#c6d2c0', null, .7);
        path([project([motor[0] - 15, motor[1] - 5, 2]), project([motor[0] + 15, motor[1] + 5, 2])], '#6d877d', null, 2.5 * scale);
      }
      path([[-22, -33, 7], [22, -33, 7], [29, 28, 7], [13, 41, 7], [-13, 41, 7], [-29, 28, 7]].map((p) => project(p)), '#213b3d', '#29474a', 1.1);
      path([[-22, -33, 7], [22, -33, 7], [22, -33, -5], [-22, -33, -5]].map((p) => project(p)), '#152e32', '#172f35', 1);
      path([[-12, -27, 9], [12, -27, 9], [0, -41, 9]].map((p) => project(p)), null, palette.lime);
      path([[-9, 7, 9], [9, 7, 9], [9, 25, 9], [-9, 25, 9]].map((p) => project(p)), '#456562', '#365753', .8);
      const front = project([0, -91, 0]); ctx.fillStyle = '#5d8070'; ctx.font = '8px Menlo, monospace'; ctx.textAlign = 'center'; ctx.fillText('FRONT', front[0], front[1] - 6);
    } else {
      path([[-50, 0, -15], [-50, 0, 30], [50, 0, 30], [50, 0, -15]].map((p) => project(p, false)), '#a4b6a1', null, 5 * scale);
      const vertices = [[-28, -20, -18], [28, -20, -18], [28, 25, -18], [-28, 25, -18], [-28, -20, 22], [28, -20, 22], [28, 25, 22], [-28, 25, 22]];
      const faces = [{ ids: [0, 1, 2, 3], color: '#1b353c' }, { ids: [3, 2, 6, 7], color: '#30515a' }, { ids: [1, 2, 6, 5], color: '#3d5d62' }, { ids: [0, 3, 7, 4], color: '#24424a' }, { ids: [4, 5, 6, 7], color: '#416665' }, { ids: [0, 1, 5, 4], color: '#213c45' }];
      faces.sort((a, b) => a.ids.reduce((sum, i) => sum + transformed(vertices[i], modelAngles)[1], 0) - b.ids.reduce((sum, i) => sum + transformed(vertices[i], modelAngles)[1], 0));
      faces.forEach((face) => path(face.ids.map((i) => project(vertices[i])), '#17333b', face.color, .7));
      const lens = Array.from({ length: 41 }, (_, i) => project([15 * Math.cos(i * Math.PI / 20), -21, 2 + 15 * Math.sin(i * Math.PI / 20)]));
      path(lens, '#83a99e', '#0e252e', 1.2 * scale);
      const glass = Array.from({ length: 33 }, (_, i) => project([9.5 * Math.cos(i * Math.PI / 16), -22, 2 + 9.5 * Math.sin(i * Math.PI / 16)]));
      path(glass, '#476e70', '#22454f', .8);
      path([project([-5, -23, 7]), project([1, -23, 11])], '#b3d5b9', null, 2 * scale);
      path([project([35, 5, 4]), project([52, 5, 4])], '#6f9482', null, 4 * scale);
    }
    // Small fixed reference triad is independent of the received pose.
    const origin = [25, h - 40];
    const triad = [[[18, 0], palette.a, 'A'], [[-9, 9], palette.b, 'B'], [[0, -18], palette.c, 'C']];
    ctx.font = '7px Menlo, monospace'; ctx.textAlign = 'center';
    for (const [delta, color, label] of triad) {
      path([origin, [origin[0] + delta[0], origin[1] + delta[1]]], color, null, 1.3);
      ctx.fillStyle = color; ctx.fillText(label, origin[0] + delta[0] * 1.35, origin[1] + delta[1] * 1.35 + 2);
    }
    if (!fresh(state?.[id])) {
      ctx.fillStyle = '#85958a'; ctx.font = '9px Menlo, monospace'; ctx.textAlign = 'center';
      ctx.fillText(validAngles(state?.[id]) ? 'LAST RECEIVED / NOT CURRENT' : 'AWAITING ORIENTATION', cx, h - 28);
    }
  }

  function drawTrace() {
    const { ctx, w, h } = canvasContext('trace-canvas');
    const left = 42, right = 12, top = 12, bottom = 28;
    const width = Math.max(1, w - left - right), height = Math.max(1, h - top - bottom);
    const now = performance.now();
    const points = history[activeTrace].filter((p) => p.time >= now - 30000);
    const data = points.map((p) => ({ time: p.time, angles: p.angles.map((angle, i) => zeros[activeTrace] ? wrap(angle - zeros[activeTrace][i]) : angle) }));
    let max = 15;
    data.forEach((p) => p.angles.forEach((a) => { max = Math.max(max, Math.abs(a) * 1.15); }));
    max = Math.ceil(Math.min(360, max) / 15) * 15;
    ctx.font = '8px Menlo, monospace'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (let n = -2; n <= 2; n++) {
      const y = top + height * (2 - n) / 4;
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + width, y); ctx.strokeStyle = n === 0 ? '#c8d2c3' : '#e5e9e0'; ctx.lineWidth = n === 0 ? 1 : .6; ctx.stroke();
      ctx.fillStyle = '#839083'; ctx.fillText(`${Math.round(max * n / 2)}°`, left - 10, y);
    }
    for (let n = 0; n <= 3; n++) {
      const x = left + width * n / 3;
      ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + height); ctx.strokeStyle = '#e5e9e0'; ctx.lineWidth = .6; ctx.stroke();
      ctx.textAlign = n === 0 ? 'left' : n === 3 ? 'right' : 'center'; ctx.fillStyle = '#899789'; ctx.fillText(n === 3 ? 'now' : `−${30 - n * 10}s`, x, h - 12);
    }
    [palette.a, palette.b, palette.c].forEach((color, index) => {
      ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 1.5;
      let previous = null;
      for (const point of data) {
        const x = left + width * (1 - (now - point.time) / 30000);
        const y = top + height / 2 - point.angles[index] / max * height / 2;
        if (!previous || point.time - previous.time > 1200 || Math.abs(point.angles[index] - previous.angles[index]) > 180) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        previous = point;
      }
      ctx.stroke();
      if (data.length) {
        const point = data[data.length - 1], x = left + width * (1 - (now - point.time) / 30000), y = top + height / 2 - point.angles[index] / max * height / 2;
        ctx.beginPath(); ctx.arc(x, y, 2.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
      }
    });
    $('trace-empty').hidden = data.length > 1;
    $('trace-empty').textContent = !data.length ? 'Waiting for received angle samples' : 'Collecting angle history…';
    const labels = activeTrace === 'aircraft' ? ['A / pitch candidate', 'B / roll candidate', 'C / yaw candidate'] : ['A / SDK pitch*', 'B / SDK roll*', 'C / SDK yaw*'];
    document.querySelectorAll('.trace-legend span').forEach((node, i) => { node.textContent = labels[i]; });
  }

  function render() { updateStatus(); updateComponents(); updateBench(); ids.forEach(drawInstrument); drawTrace(); }

  async function poll() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1500);
    try {
      const response = await fetch('/api/state', { cache: 'no-store', credentials: 'same-origin', redirect: 'error', signal: controller.signal });
      if (!response.ok) throw new Error('State unavailable');
      const next = await response.json();
      if (!next || typeof next !== 'object') throw new Error('Invalid state');
      // Markers are append-only within a session. Do not roll the guide back
      // if an in-flight poll predates a successful annotation POST.
      if (next.bench?.session_id === state?.bench?.session_id &&
          Array.isArray(next.bench?.markers) && Array.isArray(state?.bench?.markers) &&
          next.bench.markers.length < state.bench.markers.length) next.bench = state.bench;
      state = next; lastReceived = performance.now(); serviceFailed = false;
    } catch (_) { serviceFailed = true; }
    finally { clearTimeout(timeout); render(); setTimeout(poll, 100); }
  }

  for (const id of ids) $(id + '-zero').addEventListener('click', () => {
    if (!fresh(state?.[id])) return;
    zeros[id] = [...state[id].angles_deg]; render();
  });
  $('reset-zero').addEventListener('click', () => { zeros.aircraft = null; zeros.gimbal = null; render(); });
  for (const id of ids) $('trace-' + id).addEventListener('click', () => {
    activeTrace = id;
    ids.forEach((name) => { $('trace-' + name).classList.toggle('selected', name === id); $('trace-' + name).setAttribute('aria-pressed', String(name === id)); });
    drawTrace();
  });
  $('bench-record').addEventListener('click', recordMarker);
  $('bench-restart').addEventListener('click', () => {
    guideIndex = 0; guideNeedsRestart = false; guideRestartedLocally = true;
    $('bench-feedback').classList.remove('error'); $('bench-feedback').textContent = 'Guide restarted. Existing annotations are retained; the aircraft has not been commanded.'; updateBench();
  });
  window.addEventListener('resize', () => { ids.forEach(drawInstrument); drawTrace(); });
  // Refresh age indicators while a request times out or a browser tab resumes.
  setInterval(() => { if (state && elapsed() > 250) render(); }, 300);
  render(); poll();
})();
