let channelData = null;
let currentIndex = null;
let state = null;
let pollData = null;
let switching = false;

const $ = (id) => document.getElementById(id);

function formatTime(seconds) {
    const s = Math.max(0, Math.ceil(Number(seconds) || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return h ? `${h}:${m}:${sec}` : `${m}:${sec}`;
}

function updateClock() {
    $('clock').textContent = new Date().toLocaleTimeString('en-IN', { hour12: false });
}

function setPlayer(program) {
    if (!program || switching) return;
    const player = $('player');
    const source = $('videoSource');
    player.loop = true;
    if (source.src !== new URL(program.video, window.location.href).href) {
        switching = true;
        source.src = program.video;
        player.load();
        player.play().catch(() => {});
        player.addEventListener('loadedmetadata', () => { switching = false; }, { once: true });
    }
}

function renderSchedule() {
    const list = $('scheduleList');
    list.innerHTML = '';
    const programs = channelData.programs || [];
    const base = new Date((state.start_epoch || Date.now() / 1000) * 1000);
    let cursor = new Date(base);
    programs.forEach((p, i) => {
        const row = document.createElement('div');
        const active = i === currentIndex;
        const timeText = cursor.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
        row.className = 'schedule-item' + (active ? ' active' : '');
        row.innerHTML = `<div class="time">${timeText}</div><div><div class="program-title"></div><div class="program-type"></div></div><div>${active ? '<span class="now-badge">ON AIR</span>' : (i === state.next_index ? '<span class="now-badge">NEXT</span>' : '')}</div>`;
        row.querySelector('.program-title').textContent = p.title;
        row.querySelector('.program-type').textContent = p.type || 'Programme';
        list.appendChild(row);
        cursor = new Date(cursor.getTime() + Number(p.duration_seconds || 60) * 1000);
    });
}

function renderState(newState) {
    state = newState;
    const current = newState.current;
    const next = newState.next;
    if (!current) return;
    currentIndex = newState.current_index;
    $('nowTitle').textContent = current.title;
    $('nowDescription').textContent = current.description || '';
    $('nextTitle').textContent = next ? next.title : 'No upcoming programme';
    $('countdown').textContent = formatTime(newState.remaining);
    $('progressBar').style.width = `${Math.min(100, (newState.elapsed / newState.total) * 100)}%`;
    setPlayer(current);
    renderSchedule();
}

function renderPoll() {
    $('pollQuestion').textContent = pollData.question;
    const container = $('pollOptions');
    container.innerHTML = '';
    const total = Object.values(pollData.options).reduce((a, b) => a + b, 0);
    Object.entries(pollData.options).forEach(([option, votes]) => {
        const btn = document.createElement('button');
        btn.className = 'poll-btn';
        const pct = total ? Math.round((votes / total) * 100) : 0;
        btn.innerHTML = `<span></span><span class="votes">${votes} · ${pct}%</span>`;
        btn.firstElementChild.textContent = option;
        btn.onclick = async () => {
            btn.disabled = true;
            try {
                const response = await fetch('/api/poll', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({option}) });
                const result = await response.json();
                if (!result.ok) throw new Error(result.error || 'Vote failed');
                pollData = result.poll;
                $('pollMessage').textContent = 'Thanks — your vote has been recorded.';
                renderPoll();
            } catch (err) {
                $('pollMessage').textContent = err.message;
                btn.disabled = false;
            }
        };
        container.appendChild(btn);
    });
}

async function refreshState() {
    try {
        const response = await fetch('/api/channel/state', { cache: 'no-store' });
        const newState = await response.json();
        if (state === null || newState.current_index !== currentIndex) renderState(newState);
        else {
            state = newState;
            $('countdown').textContent = formatTime(newState.remaining);
            $('progressBar').style.width = `${Math.min(100, (newState.elapsed / newState.total) * 100)}%`;
        }
    } catch (err) {
        console.error('Channel state error:', err);
    }
}

async function init() {
    const response = await fetch('/api/channel', { cache: 'no-store' });
    channelData = await response.json();
    pollData = channelData.poll;
    renderState({ ...channelData.state, current: channelData.programs[channelData.state.current_index], next: channelData.programs[channelData.state.next_index] });
    renderPoll();
    updateClock();
    setInterval(updateClock, 1000);
    setInterval(refreshState, 1000);
}

init().catch(err => {
    console.error(err);
    $('nowTitle').textContent = 'Channel temporarily unavailable';
    $('nowDescription').textContent = 'Please check that the Flask server is running.';
});
