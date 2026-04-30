/**
 * Team Task Manager – Frontend Application v4
 * Upgrades: User assignment dropdown, My Tasks, status transitions, overdue badges, action logging.
 */

const API = '/api/v1';

// ──────────────── State ────────────────
let token       = localStorage.getItem('ttm_token') || null;
let currentUser = JSON.parse(localStorage.getItem('ttm_user') || 'null');
let activeRequests = 0;
let allUsers = [];

// ──────────────── Core Helpers ────────────────

function showLoader() {
  if (activeRequests++ === 0) {
    const loader = document.getElementById('global-loader');
    loader.classList.remove('hidden');
    setTimeout(() => { loader.style.opacity = '1'; }, 10);
  }
}

function hideLoader() {
  if (--activeRequests === 0) {
    const loader = document.getElementById('global-loader');
    loader.style.opacity = '0';
    setTimeout(() => { if (activeRequests === 0) loader.classList.add('hidden'); }, 300);
  }
}

function headers() {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

async function api(path, opts = {}) {
  showLoader();
  try {
    const res  = await fetch(`${API}${path}`, { headers: headers(), ...opts });
    const body = await res.json();
    if (!res.ok) {
      if (res.status === 401 && path !== '/auth/login' && path !== '/auth/me') {
        handleLogout();
        showToast('Session expired. Please log in again.', 'error');
        throw new Error('Session expired');
      }
      throw new Error(body.message || body.detail || 'Request failed');
    }
    return body;
  } catch (err) {
    showToast(err.message, 'error');
    throw err;
  } finally {
    hideLoader();
  }
}

function showToast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .4s ease'; }, 2800);
  setTimeout(() => el.remove(), 3200);
}

function isAdmin() { return currentUser && currentUser.role === 'Admin'; }

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function toInputDate(iso) {
  if (!iso) return '';
  return new Date(iso).toISOString().slice(0, 10);
}

function statusClass(s) {
  if (s === 'Pending')     return 'status-pending';
  if (s === 'In Progress') return 'status-inprogress';
  return 'status-completed';
}

function priorityClass(p) {
  if (p === 'Low')  return 'priority-low';
  if (p === 'High') return 'priority-high';
  return 'priority-medium';
}

function esc(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

function togglePassword(inputId) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}

// ──────────────── Auth ────────────────

function switchAuthTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('login-form').classList.toggle('hidden', !isLogin);
  document.getElementById('register-form').classList.toggle('hidden', isLogin);
  document.getElementById('tab-login').className   = `flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 ease-in-out ${isLogin ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`;
  document.getElementById('tab-register').className = `flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 ease-in-out ${!isLogin ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`;
}

async function handleLogin(e) {
  e.preventDefault();
  try {
    const res = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username: document.getElementById('login-username').value.trim(),
        password: document.getElementById('login-password').value,
      }),
    });
    saveAuth(res.data);
    showToast('Welcome back, ' + res.data.user.username + '!');
    enterDashboard();
  } catch (_) {}
}

async function handleRegister(e) {
  e.preventDefault();
  try {
    const res = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: document.getElementById('reg-username').value.trim(),
        email:    document.getElementById('reg-email').value.trim(),
        password: document.getElementById('reg-password').value,
        role:     document.getElementById('reg-role').value,
      }),
    });
    saveAuth(res.data);
    showToast('Account created successfully!');
    enterDashboard();
  } catch (_) {}
}

function saveAuth(data) {
  token       = data.access_token;
  currentUser = data.user;
  localStorage.setItem('ttm_token', token);
  localStorage.setItem('ttm_user', JSON.stringify(currentUser));
}

function handleLogout() {
  token = null; currentUser = null;
  localStorage.removeItem('ttm_token');
  localStorage.removeItem('ttm_user');
  document.getElementById('dashboard').classList.add('hidden');
  document.getElementById('auth-screen').classList.remove('hidden');
  showToast('Logged out successfully');
}

// ──────────────── Dashboard ────────────────

async function enterDashboard() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('dashboard').classList.remove('hidden');
  document.getElementById('nav-username').textContent = currentUser.username;
  document.getElementById('nav-role').textContent     = currentUser.role;

  const adminBoxes = ['create-project-box', 'create-task-box', 'analytics-strip'];
  adminBoxes.forEach(id => {
    document.getElementById(id).classList.toggle('hidden', !isAdmin());
  });

  // Hide My Tasks tab for Admins
  document.getElementById('sec-btn-mytasks').classList.toggle('hidden', isAdmin());

  await loadUsers();
  showSection('projects');
  await loadProjects();
  if (isAdmin()) await loadAnalytics();
}

async function loadUsers() {
  try {
    const res = await api('/auth/users');
    allUsers = res.data || [];
    populateUserSelects();
  } catch (_) {}
}

function populateUserSelects() {
  const sel = document.getElementById('task-assignee');
  sel.innerHTML = '<option value="">Unassigned</option>';
  allUsers.forEach(u => {
    sel.innerHTML += `<option value="${u.id}">${esc(u.username)} (${u.role})</option>`;
  });
}

function showSection(name) {
  ['projects', 'tasks', 'mytasks'].forEach(s => {
    document.getElementById(`section-${s}`).classList.toggle('hidden', s !== name);
    const btn = document.getElementById(`sec-btn-${s}`);
    if (btn) {
      btn.className = s === name
        ? 'flex-1 sm:flex-none px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 ease-in-out bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-inner'
        : 'flex-1 sm:flex-none px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 ease-in-out text-gray-400 hover:text-white hover:bg-gray-800/80 border border-transparent hover:border-gray-700';
      if (s === 'mytasks' && isAdmin()) {
        btn.classList.add('hidden');
      }
    }
  });
  if (name === 'projects') loadProjects();
  if (name === 'tasks')    loadTasks();
  if (name === 'mytasks')  loadMyTasks();
}

// ──────────────── Analytics ────────────────

async function loadAnalytics() {
  try {
    const res = await api('/analytics/');
    const d   = res.data;
    document.getElementById('m-total-tasks').textContent = d.total_tasks;
    document.getElementById('m-completed').textContent   = d.completed_tasks;
    document.getElementById('m-pending').textContent     = d.pending_tasks;
    document.getElementById('m-overdue').textContent     = d.overdue_tasks;
  } catch (_) {}
}

// ──────────────── Projects ────────────────

async function loadProjects() {
  try {
    const res      = await api('/projects/?limit=100');
    const projects = res.data || [];
    const container = document.getElementById('project-list');
    const noEl      = document.getElementById('no-projects');

    if (projects.length === 0) {
      container.innerHTML = '';
      noEl.classList.remove('hidden');
      return;
    }
    noEl.classList.add('hidden');

    container.innerHTML = projects.map(p => `
      <div class="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-6 transition-all duration-300 ease-in-out hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10 hover:border-indigo-500/30 cursor-pointer group fade-in"
           onclick="filterTasksByProject('${p.id}')">
        <div class="flex items-start justify-between mb-4">
          <h3 class="font-bold text-white text-lg group-hover:text-indigo-300 transition-colors duration-300 line-clamp-1 pr-2">${esc(p.name)}</h3>
          <span class="text-[10px] text-gray-500 font-mono bg-gray-900/50 px-2 py-1 rounded border border-white/5">${p.id.slice(0,8)}</span>
        </div>
        <p class="text-sm text-gray-400 mb-6 line-clamp-2 h-10">${esc(p.description || 'No description provided.')}</p>
        <div class="flex items-center justify-between text-xs text-gray-500 border-t border-gray-800 pt-4">
          <span>Created ${formatDate(p.created_at)}</span>
          <span class="text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300 font-medium flex items-center gap-1">
            Tasks <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
          </span>
        </div>
      </div>
    `).join('');

    populateProjectSelects(projects);
  } catch (_) {}
}

function populateProjectSelects(projects) {
  ['task-project', 'task-filter-project'].forEach((id, i) => {
    const sel = document.getElementById(id);
    const cur = sel.value;
    sel.innerHTML = i === 0
      ? '<option value="">Select Project</option>'
      : '<option value="">All Projects</option>';
    projects.forEach(p => { sel.innerHTML += `<option value="${p.id}">${esc(p.name)}</option>`; });
    sel.value = cur;
  });
}

async function handleCreateProject(e) {
  e.preventDefault();
  try {
    await api('/projects/', {
      method: 'POST',
      body: JSON.stringify({
        name:        document.getElementById('proj-name').value.trim(),
        description: document.getElementById('proj-desc').value.trim(),
      }),
    });
    showToast('Project created successfully!');
    document.getElementById('project-form').reset();
    await loadProjects();
    if (isAdmin()) await loadAnalytics();
  } catch (_) {}
}

function filterTasksByProject(projectId) {
  document.getElementById('task-filter-project').value = projectId;
  showSection('tasks');
}

// ──────────────── Task Card Renderer ────────────────

function renderTaskCard(t, showUpdateBtn = true) {
  const canUpdate  = showUpdateBtn && (isAdmin() || t.assigned_to_id === currentUser.id);
  const overdue    = t.is_overdue;
  const needsApproval = t.needs_admin_approval;
  
  let cardBorder = 'border-white/10 hover:border-indigo-500/30';
  if (needsApproval) cardBorder = 'border-yellow-500/50 task-pending-approval';
  else if (overdue) cardBorder = 'task-overdue border-red-500/50';

  return `
    <div class="bg-white/5 backdrop-blur-md border rounded-2xl p-6 transition-all duration-300 ease-in-out hover:scale-[1.02] hover:shadow-xl hover:shadow-indigo-500/10 fade-in flex flex-col ${cardBorder}">
      <div class="flex-1">
        <div class="flex items-start justify-between gap-2 mb-3">
          <h3 class="font-bold text-white text-lg line-clamp-1 pr-2" title="${esc(t.title)}">${esc(t.title)}</h3>
          ${canUpdate ? `
            <button onclick='openUpdateModal(${JSON.stringify(t).replace(/'/g, "\\\\'").replace(/\//g, "\\/")})'
                    class="bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white p-2 rounded-lg transition-colors duration-300 border border-white/5 shadow-sm" aria-label="Edit Task">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
            </button>
          ` : ''}
        </div>
        
        <div class="flex flex-wrap items-center gap-2 mb-4">
          <span class="text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${statusClass(t.status)}">${t.status}</span>
          <span class="text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${priorityClass(t.priority)}">${t.priority}</span>
          ${overdue && !needsApproval ? '<span class="overdue-badge shadow-sm shadow-red-500/20 text-[10px] px-2 py-1 rounded-full font-bold bg-red-500/20 text-red-300">⚠ Overdue</span>' : ''}
          ${needsApproval ? '<span class="shadow-sm shadow-yellow-500/20 text-[10px] px-2 py-1 rounded-full font-bold bg-yellow-500/20 text-yellow-300">⏳ Pending Approval</span>' : ''}
        </div>
        
        <p class="text-sm text-gray-400 mb-5 line-clamp-2">${esc(t.description || 'No description provided.')}</p>
      </div>
      
      <div class="border-t border-gray-800 pt-4 mt-auto">
        <div class="grid grid-cols-2 gap-y-3 gap-x-2 text-[11px] text-gray-500 font-medium">
          <div class="flex flex-col gap-1">
            <span class="text-gray-600 uppercase tracking-wider text-[9px] font-bold">Assigned to</span>
            <span class="text-gray-400 truncate">${t.assigned_to_username ? esc(t.assigned_to_username) : '<span class=&quot;text-gray-600 italic&quot;>Unassigned</span>'}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-gray-600 uppercase tracking-wider text-[9px] font-bold">Due Date</span>
            <span class="${overdue ? 'text-red-400 font-bold' : 'text-gray-400'}">${formatDate(t.due_date)}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-gray-600 uppercase tracking-wider text-[9px] font-bold">Project ID</span>
            <span class="text-gray-400 font-mono truncate bg-gray-900/50 px-2 py-0.5 rounded w-fit">${t.project_id.slice(0,8)}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-gray-600 uppercase tracking-wider text-[9px] font-bold">Updated</span>
            <span class="text-gray-400">${formatDate(t.updated_at)}</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ──────────────── Tasks ────────────────

async function loadTasks() {
  try {
    const projectId = document.getElementById('task-filter-project').value;
    const query     = projectId ? `?project_id=${projectId}&limit=100` : '?limit=100';
    const res       = await api(`/tasks/${query}`);
    const tasks     = res.data || [];
    const container = document.getElementById('task-list');
    const noEl      = document.getElementById('no-tasks');

    if (tasks.length === 0) {
      container.innerHTML = '';
      noEl.classList.remove('hidden');
      return;
    }
    noEl.classList.add('hidden');
    container.innerHTML = tasks.map(t => renderTaskCard(t)).join('');
  } catch (_) {}
}

// ──────────────── My Tasks ────────────────

async function loadMyTasks() {
  try {
    const res   = await api('/tasks/my?limit=100');
    const tasks = res.data || [];
    const container = document.getElementById('mytask-list');
    const noEl      = document.getElementById('no-mytasks');

    if (tasks.length === 0) {
      container.innerHTML = '';
      noEl.classList.remove('hidden');
      return;
    }
    noEl.classList.add('hidden');
    container.innerHTML = tasks.map(t => renderTaskCard(t)).join('');
  } catch (_) {}
}

// ──────────────── Create Task ────────────────

async function handleCreateTask(e) {
  e.preventDefault();
  const dueDateVal = document.getElementById('task-due-date').value;
  if (!dueDateVal) {
    showToast('Due date is required', 'error');
    return;
  }
  const payload = {
    title:          document.getElementById('task-title').value.trim(),
    project_id:     document.getElementById('task-project').value,
    description:    document.getElementById('task-desc').value.trim(),
    assigned_to_id: document.getElementById('task-assignee').value || null,
    priority:       document.getElementById('task-priority').value || null,
    due_date:       new Date(dueDateVal).toISOString(),
  };
  try {
    await api('/tasks/', { method: 'POST', body: JSON.stringify(payload) });
    showToast('Task created successfully!');
    document.getElementById('task-form').reset();
    await loadTasks();
    if (isAdmin()) await loadAnalytics();
  } catch (_) {}
}

// ──────────────── Update Task Modal ────────────────

function openUpdateModal(task) {
  const modal = document.getElementById('update-modal');
  modal.classList.remove('hidden');
  
  const dialog = modal.querySelector('.slide-up');
  dialog.style.animation = 'none';
  dialog.offsetHeight;
  dialog.style.animation = null;

  document.getElementById('update-task-id').value     = task.id;
  document.getElementById('modal-task-title').textContent = task.title;
  document.getElementById('update-status').value      = task.status;

  // Show valid transition hint
  const statusHint = document.getElementById('status-transition-hint');
  const transitions = {
    'Pending': 'Pending → In Progress',
    'In Progress': 'In Progress → Completed',
    'Completed': 'No further transitions allowed',
  };
  statusHint.textContent = transitions[task.status] || '';

  const adminFields = document.getElementById('admin-update-fields');
  const approvalHint = document.getElementById('approval-hint');
  
  if (approvalHint) approvalHint.remove();

  if (isAdmin()) {
    adminFields.classList.remove('hidden');
    document.getElementById('update-title').value    = task.title;
    document.getElementById('update-desc').value     = task.description || '';
    document.getElementById('update-priority').value = task.priority || 'Medium';
    document.getElementById('update-due-date').value = toInputDate(task.due_date);
    
    if (task.needs_admin_approval) {
      statusHint.textContent = "User has requested to complete this task. Change status to 'Completed' to approve.";
      statusHint.className = "text-xs text-yellow-500 mt-2 font-semibold";
    } else {
      statusHint.className = "text-xs text-gray-500 mt-2 italic";
    }
  } else {
    adminFields.classList.add('hidden');
    statusHint.className = "text-xs text-gray-500 mt-2 italic";
    if (task.status !== 'Completed') {
       const hintMsg = document.createElement('p');
       hintMsg.id = 'approval-hint';
       hintMsg.className = "text-xs text-indigo-400 mt-2";
       hintMsg.textContent = "Setting status to Completed will submit it for Admin approval.";
       statusHint.parentNode.insertBefore(hintMsg, statusHint.nextSibling);
    }
  }
}

function closeModal() {
  document.getElementById('update-modal').classList.add('hidden');
}

async function handleUpdateTask(e) {
  e.preventDefault();
  const taskId  = document.getElementById('update-task-id').value;
  const payload = { status: document.getElementById('update-status').value };

  if (isAdmin()) {
    const title   = document.getElementById('update-title').value.trim();
    const desc    = document.getElementById('update-desc').value.trim();
    const prio    = document.getElementById('update-priority').value;
    const dueVal  = document.getElementById('update-due-date').value;
    if (title) payload.title            = title;
    payload.description                 = desc;
    payload.priority                    = prio;
    payload.due_date                    = dueVal ? new Date(dueVal).toISOString() : null;
  }

  try {
    await api(`/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(payload) });
    showToast('Task updated successfully!');
    closeModal();
    await loadTasks();
    await loadMyTasks();
    if (isAdmin()) await loadAnalytics();
  } catch (_) {}
}

// ──────────────── Init ────────────────

(function init() {
  if (token && currentUser) {
    fetch(`${API}/auth/me`, { headers: headers() })
      .then(r => r.ok ? enterDashboard() : handleLogout())
      .catch(() => handleLogout());
  }
})();

// Expose to global scope for inline onclick handlers
Object.assign(window, {
  switchAuthTab, handleLogin, handleRegister, handleLogout,
  showSection, handleCreateProject, handleCreateTask,
  handleUpdateTask, openUpdateModal, closeModal,
  filterTasksByProject, loadTasks, loadMyTasks, loadAnalytics, togglePassword
});
