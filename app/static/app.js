// Frontend sin framework para que el laboratorio sea fácil de revisar y ejecutar.
const state = {
  roomCode: window.INITIAL_ROOM_CODE || localStorage.getItem('roomCode') || '',
  participantId: localStorage.getItem('participantId') || '',
  participantName: localStorage.getItem('participantName') || '',
  matches: []
};

const $ = (selector) => document.querySelector(selector);
const createdRoom = $('#createdRoom');
const activeRoom = $('#activeRoom');
const matchesList = $('#matchesList');
const leaderboardBody = $('#leaderboardBody');
const statsBox = $('#stats');

function showNotice(element, html) {
  element.innerHTML = html;
  element.classList.remove('hidden');
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || 'Ocurrió un error inesperado');
  }
  return data;
}

function persistSession() {
  if (state.roomCode) localStorage.setItem('roomCode', state.roomCode);
  if (state.participantId) localStorage.setItem('participantId', state.participantId);
  if (state.participantName) localStorage.setItem('participantName', state.participantName);
}

function formatDate(value) {
  return new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value));
}

async function loadMatches() {
  const data = await api('/api/matches');
  state.matches = data.matches;
  renderMatches();
}

function renderMatches() {
  matchesList.innerHTML = '';
  const template = $('#matchTemplate');

  state.matches.forEach((match) => {
    const node = template.content.cloneNode(true);
    const article = node.querySelector('.match-card');
    const title = node.querySelector('h3');
    const status = node.querySelector('.status');
    const date = node.querySelector('.match-date');
    const predictionForm = node.querySelector('.prediction-form');
    const resultForm = node.querySelector('.result-form');

    title.textContent = `${match.home_team} vs ${match.away_team}`;
    status.textContent = match.status === 'finished' ? `Final: ${match.home_score}-${match.away_score}` : 'Programado';
    date.textContent = `Inicio: ${formatDate(match.starts_at)}`;

    predictionForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!state.participantId) {
        alert('Primero entra o regístrate en una sala.');
        return;
      }
      const form = new FormData(predictionForm);
      try {
        await api('/api/predictions', {
          method: 'POST',
          body: JSON.stringify({
            participant_id: state.participantId,
            match_id: match.id,
            pred_home: form.get('pred_home'),
            pred_away: form.get('pred_away')
          })
        });
        alert('Predicción guardada correctamente.');
        await loadLeaderboard();
      } catch (error) {
        alert(error.message);
      }
    });

    resultForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(resultForm);
      try {
        await api(`/api/matches/${match.id}/result`, {
          method: 'PATCH',
          body: JSON.stringify({
            home_score: form.get('home_score'),
            away_score: form.get('away_score')
          })
        });
        await loadMatches();
        await loadLeaderboard();
      } catch (error) {
        alert(error.message);
      }
    });

    matchesList.appendChild(article);
  });
}

async function loadRoom(code) {
  const data = await api(`/api/rooms/${code}`);
  const participants = data.participants.map(p => p.name).join(', ') || 'Sin participantes';
  showNotice(activeRoom, `<strong>Sala activa:</strong> ${data.room.name}<br><strong>Código:</strong> ${data.room.code}<br><strong>Participantes:</strong> ${participants}<br><strong>Sesión:</strong> ${state.participantName || 'sin participante seleccionado'}`);
}

async function loadLeaderboard() {
  if (!state.roomCode) return;
  const [boardData, statsData] = await Promise.all([
    api(`/api/rooms/${state.roomCode}/leaderboard`),
    api(`/api/stats/${state.roomCode}`)
  ]);

  leaderboardBody.innerHTML = '';
  boardData.leaderboard.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.position}</td>
      <td>${row.name}</td>
      <td>${row.matches_evaluated}</td>
      <td>${row.points_base_and_early}</td>
      <td>${row.streak_bonus}</td>
      <td>${row.total_points}</td>
    `;
    leaderboardBody.appendChild(tr);
  });

  statsBox.innerHTML = `
    <div class="stat-card"><span>Participantes</span><strong>${statsData.participants}</strong></div>
    <div class="stat-card"><span>Predicciones</span><strong>${statsData.predictions}</strong></div>
    <div class="stat-card"><span>Partidos finalizados</span><strong>${statsData.finished_matches}</strong></div>
    <div class="stat-card"><span>Líder</span><strong>${statsData.leader ? statsData.leader.name : '-'}</strong></div>
    <div class="stat-card"><span>Nodo API</span><strong>${statsData.node}</strong></div>
  `;
}

$('#createRoomForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const data = await api('/api/rooms', {
      method: 'POST',
      body: JSON.stringify({ name: form.get('name'), owner_name: form.get('owner_name') })
    });
    state.roomCode = data.room.code;
    state.participantId = data.owner_participant.id;
    state.participantName = data.owner_participant.name;
    persistSession();
    $('#roomCodeInput').value = state.roomCode;
    showNotice(createdRoom, `<strong>Sala creada:</strong> ${data.room.name}<br><strong>Código de invitación:</strong> ${data.room.code}<br><strong>URL:</strong> <a href="${data.invite_url}">${data.invite_url}</a>`);
    await loadRoom(state.roomCode);
    await loadLeaderboard();
  } catch (error) {
    alert(error.message);
  }
});

$('#joinRoomForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const code = String(form.get('code')).trim().toUpperCase();
  const name = String(form.get('participant_name')).trim();
  try {
    const data = await api(`/api/rooms/${code}/participants`, {
      method: 'POST',
      body: JSON.stringify({ name })
    });
    state.roomCode = code;
    state.participantId = data.participant.id;
    state.participantName = data.participant.name;
    persistSession();
    await loadRoom(code);
    await loadLeaderboard();
  } catch (error) {
    alert(error.message);
  }
});

$('#createMatchForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const startsAtLocal = form.get('starts_at');
  const startsAtIso = new Date(startsAtLocal).toISOString();
  try {
    await api('/api/matches', {
      method: 'POST',
      body: JSON.stringify({
        home_team: form.get('home_team'),
        away_team: form.get('away_team'),
        starts_at: startsAtIso
      })
    });
    event.currentTarget.reset();
    await loadMatches();
  } catch (error) {
    alert(error.message);
  }
});

$('#refreshMatchesBtn').addEventListener('click', loadMatches);
$('#refreshLeaderboardBtn').addEventListener('click', loadLeaderboard);

(async function boot() {
  try {
    if (state.roomCode) {
      $('#roomCodeInput').value = state.roomCode;
      await loadRoom(state.roomCode);
      await loadLeaderboard();
    }
    await loadMatches();
  } catch (error) {
    console.warn(error);
  }
})();
