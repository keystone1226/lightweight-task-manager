/* ── State ──────────────────────────────────────── */
let currentUser = null;
let allUsers = [];
let columns = [];
let tasks = [];
let notifPanelOpen = false;

const TAG_COLORS = [
  '#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#8b5cf6',
  '#ef4444', '#06b6d4', '#84cc16', '#f97316', '#64748b',
];

function tagColor(tag) {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length];
}

/* ── API helpers ────────────────────────────────── */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

/* ── Init ───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  const saved = localStorage.getItem('taskmanager_user');
  if (saved) {
    try {
      currentUser = JSON.parse(saved);
      // Re-register (idempotent)
      currentUser = await api('/api/users', {
        method: 'POST',
        body: JSON.stringify({ nickname: currentUser.nickname, email: currentUser.email }),
      });
      localStorage.setItem('taskmanager_user', JSON.stringify(currentUser));
    } catch {
      localStorage.removeItem('taskmanager_user');
      currentUser = null;
    }
  }

  if (!currentUser) {
    showNicknameModal();
  } else {
    startApp();
  }
});

/* ── Nickname Modal ─────────────────────────────── */
function showNicknameModal() {
  document.getElementById('nicknameModal').classList.add('active');
  document.getElementById('nicknameInput').focus();
}

document.getElementById('nicknameSubmit').addEventListener('click', async () => {
  const nickname = document.getElementById('nicknameInput').value.trim();
  if (!nickname) return;
  const email = document.getElementById('emailInput').value.trim() || null;
  try {
    currentUser = await api('/api/users', {
      method: 'POST',
      body: JSON.stringify({ nickname, email }),
    });
    localStorage.setItem('taskmanager_user', JSON.stringify(currentUser));
    document.getElementById('nicknameModal').classList.remove('active');
    startApp();
  } catch (e) {
    alert('Error: ' + e.message);
  }
});

document.getElementById('nicknameInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('nicknameSubmit').click();
});

/* ── Start App ──────────────────────────────────── */
async function startApp() {
  document.getElementById('currentUserName').textContent = currentUser.nickname;
  await Promise.all([loadColumns(), loadUsers()]);
  await loadTasks();
  renderBoard();
  pollNotifications();
  setInterval(pollNotifications, 30000);
}

/* ── Data Loading ───────────────────────────────── */
async function loadColumns() {
  columns = await api('/api/columns');
}

async function loadUsers() {
  allUsers = await api('/api/users');
}

async function loadTasks() {
  tasks = await api('/api/tasks');
}

/* ── Notifications ──────────────────────────────── */
async function pollNotifications() {
  if (!currentUser) return;
  try {
    const data = await api(`/api/users/${currentUser.id}/notifications/count`);
    const badge = document.getElementById('notifBadge');
    if (data.unread_count > 0) {
      badge.textContent = data.unread_count;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  } catch {}
}

document.getElementById('notifBell').addEventListener('click', async () => {
  notifPanelOpen = !notifPanelOpen;
  const panel = document.getElementById('notifPanel');
  if (notifPanelOpen) {
    panel.classList.add('active');
    const notifications = await api(`/api/users/${currentUser.id}/notifications`);
    renderNotifications(notifications);
  } else {
    panel.classList.remove('active');
  }
});

document.getElementById('markAllRead').addEventListener('click', async () => {
  await api(`/api/users/${currentUser.id}/notifications/read-all`, { method: 'POST' });
  pollNotifications();
  const notifications = await api(`/api/users/${currentUser.id}/notifications`);
  renderNotifications(notifications);
});

function renderNotifications(notifications) {
  const list = document.getElementById('notifList');
  if (!notifications.length) {
    list.innerHTML = '<div class="notification-empty">No notifications</div>';
    return;
  }
  list.innerHTML = notifications.map(n => `
    <div class="notification-item ${n.is_read ? '' : 'unread'}"
         data-id="${n.id}" data-task-id="${n.task_id}">
      <div>${n.message}</div>
      <div class="notif-time">${timeAgo(n.created_at)}</div>
    </div>
  `).join('');

  list.querySelectorAll('.notification-item').forEach(el => {
    el.addEventListener('click', async () => {
      await api(`/api/notifications/${el.dataset.id}/read`, { method: 'PATCH' });
      el.classList.remove('unread');
      pollNotifications();
      const taskId = parseInt(el.dataset.taskId);
      const task = tasks.find(t => t.id === taskId);
      if (task) openTaskModal(task);
    });
  });
}

/* ── Board Rendering ────────────────────────────── */
function renderBoard() {
  const board = document.getElementById('board');
  board.innerHTML = '';

  columns.forEach(col => {
    const colTasks = tasks.filter(t => t.status === col.name)
      .sort((a, b) => a.sort_order - b.sort_order);

    const colEl = document.createElement('div');
    colEl.className = 'column';
    colEl.innerHTML = `
      <div class="column-color-bar" style="background:${col.color || '#6b7280'}"></div>
      <div class="column-header">
        <span>${col.name.replace(/_/g, ' ')}</span>
        <span class="count">${colTasks.length}</span>
      </div>
      <div class="column-body" data-status="${col.name}">
        ${colTasks.map(t => renderTaskCard(t)).join('')}
        <button class="add-task-btn" data-status="${col.name}">+ Add Task</button>
      </div>
    `;
    board.appendChild(colEl);

    // Drag & drop
    const body = colEl.querySelector('.column-body');
    body.addEventListener('dragover', e => {
      e.preventDefault();
      body.classList.add('drag-over');
    });
    body.addEventListener('dragleave', () => body.classList.remove('drag-over'));
    body.addEventListener('drop', async e => {
      e.preventDefault();
      body.classList.remove('drag-over');
      const taskId = parseInt(e.dataTransfer.getData('text/plain'));
      const newStatus = body.dataset.status;
      try {
        await api(`/api/tasks/${taskId}/status`, {
          method: 'PATCH',
          body: JSON.stringify({ status: newStatus, sort_order: 0 }),
        });
        await loadTasks();
        renderBoard();
      } catch {}
    });

    // Add task button
    colEl.querySelector('.add-task-btn').addEventListener('click', () => {
      openTaskModal(null, col.name);
    });
  });

  // Card event listeners
  board.querySelectorAll('.task-card').forEach(card => {
    card.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/plain', card.dataset.id);
      card.classList.add('dragging');
    });
    card.addEventListener('dragend', () => card.classList.remove('dragging'));
    card.addEventListener('click', () => {
      const task = tasks.find(t => t.id === parseInt(card.dataset.id));
      if (task) openTaskModal(task);
    });
  });
}

function renderTaskCard(task) {
  const tags = parseTags(task.tags);
  const dueDateHtml = task.due_date ? renderDueDate(task.due_date) : '';
  const assignee = task.assignee_user ? task.assignee_user.nickname : '';
  const coverImg = task.image_path
    ? `<img class="task-card-cover" src="${task.image_path}" alt="cover">`
    : '';

  const linkIcons = [];
  if (task.link_url) {
    linkIcons.push(`<a class="link-icon" href="${escHtml(task.link_url)}" target="_blank" title="Link" onclick="event.stopPropagation()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
    </a>`);
  }

  return `
    <div class="task-card" draggable="true" data-id="${task.id}">
      ${coverImg}
      <div class="task-card-title">${escHtml(task.title)}</div>
      <div class="task-card-meta">
        <span class="priority-badge priority-${task.priority}">${task.priority}</span>
        ${tags.map(t => `<span class="tag-badge" style="background:${tagColor(t)}22;color:${tagColor(t)}">${escHtml(t)}</span>`).join('')}
        ${linkIcons.join('')}
        ${dueDateHtml}
        ${assignee ? `<span class="assignee-badge">${escHtml(assignee)}</span>` : ''}
      </div>
    </div>
  `;
}

/* ── Task Modal ─────────────────────────────────── */
function openTaskModal(task, defaultStatus) {
  const modal = document.getElementById('taskModal');
  const title = document.getElementById('taskModalTitle');
  const form = document.getElementById('taskForm');
  const deleteBtn = document.getElementById('deleteTaskBtn');
  const commentsSection = document.getElementById('commentsSection');

  // Populate assignee dropdown
  const assigneeSelect = document.getElementById('taskAssignee');
  assigneeSelect.innerHTML = '<option value="">Unassigned</option>' +
    allUsers.map(u => `<option value="${u.id}">${escHtml(u.nickname)}</option>`).join('');

  if (task) {
    title.textContent = 'Edit Task';
    document.getElementById('taskId').value = task.id;
    document.getElementById('taskStatus').value = task.status;
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDesc').value = task.description || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskAssignee').value = task.assignee_id || '';
    document.getElementById('taskDueDate').value = task.due_date || '';
    document.getElementById('taskTags').value = parseTags(task.tags).join(', ');
    document.getElementById('taskLinkUrl').value = task.link_url || '';
    if (task.link_url) fetchOGPreview(task.link_url);
    else clearOGPreview();
    deleteBtn.style.display = 'block';
    commentsSection.style.display = 'block';
    loadComments(task.id);

    if (task.image_path) {
      const preview = document.getElementById('imagePreview');
      preview.src = task.image_path;
      preview.style.display = 'block';
    } else {
      document.getElementById('imagePreview').style.display = 'none';
    }
  } else {
    title.textContent = 'New Task';
    form.reset();
    document.getElementById('taskId').value = '';
    document.getElementById('taskStatus').value = defaultStatus || 'TODO';
    deleteBtn.style.display = 'none';
    commentsSection.style.display = 'none';
    document.getElementById('imagePreview').style.display = 'none';
    clearOGPreview();
  }

  modal.classList.add('active');
  document.getElementById('taskTitle').focus();
}

function closeTaskModal() {
  document.getElementById('taskModal').classList.remove('active');
}

document.getElementById('cancelTaskBtn').addEventListener('click', closeTaskModal);
document.getElementById('taskModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeTaskModal();
});

document.getElementById('taskForm').addEventListener('submit', async e => {
  e.preventDefault();
  const id = document.getElementById('taskId').value;
  const tagsRaw = document.getElementById('taskTags').value;
  const tags = tagsRaw
    ? JSON.stringify(tagsRaw.split(',').map(t => t.trim()).filter(Boolean))
    : null;

  const data = {
    title: document.getElementById('taskTitle').value,
    description: document.getElementById('taskDesc').value || null,
    status: document.getElementById('taskStatus').value,
    priority: document.getElementById('taskPriority').value,
    assignee_id: document.getElementById('taskAssignee').value || null,
    due_date: document.getElementById('taskDueDate').value || null,
    tags,
    link_url: document.getElementById('taskLinkUrl').value || null,
  };

  if (data.assignee_id) data.assignee_id = parseInt(data.assignee_id);

  try {
    let savedTask;
    if (id) {
      savedTask = await api(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
    } else {
      savedTask = await api('/api/tasks', { method: 'POST', body: JSON.stringify(data) });
    }

    // Upload image if selected
    const imageInput = document.getElementById('imageInput');
    if (imageInput.files.length > 0) {
      const formData = new FormData();
      formData.append('file', imageInput.files[0]);
      await fetch(`/api/tasks/${savedTask.id}/image`, { method: 'POST', body: formData });
    }

    await loadTasks();
    renderBoard();
    closeTaskModal();
  } catch (err) {
    alert('Error: ' + err.message);
  }
});

document.getElementById('deleteTaskBtn').addEventListener('click', async () => {
  const id = document.getElementById('taskId').value;
  if (!id || !confirm('Delete this task?')) return;
  await api(`/api/tasks/${id}`, { method: 'DELETE' });
  await loadTasks();
  renderBoard();
  closeTaskModal();
});

/* ── OG Preview ─────────────────────────────────── */
let ogDebounceTimer = null;

document.getElementById('taskLinkUrl').addEventListener('input', () => {
  clearTimeout(ogDebounceTimer);
  const url = document.getElementById('taskLinkUrl').value.trim();
  if (!url) { clearOGPreview(); return; }
  ogDebounceTimer = setTimeout(() => fetchOGPreview(url), 800);
});

async function fetchOGPreview(url) {
  try {
    const data = await api(`/api/og-preview?url=${encodeURIComponent(url)}`);
    if (!data.title && !data.image) { clearOGPreview(); return; }
    showOGPreview(data);
  } catch {
    clearOGPreview();
  }
}

function showOGPreview(data) {
  const preview = document.getElementById('ogPreview');
  const img = document.getElementById('ogPreviewImage');
  document.getElementById('ogPreviewSite').textContent = data.site_name || '';
  document.getElementById('ogPreviewTitle').textContent = data.title || '';
  document.getElementById('ogPreviewDesc').textContent = data.description || '';
  if (data.image) {
    img.src = data.image;
    img.style.display = 'block';
  } else {
    img.style.display = 'none';
  }
  preview.style.display = 'flex';
}

function clearOGPreview() {
  document.getElementById('ogPreview').style.display = 'none';
  document.getElementById('ogPreviewImage').style.display = 'none';
}

/* ── Image Upload ───────────────────────────────── */
const imageUploadArea = document.getElementById('imageUploadArea');
const imageInput = document.getElementById('imageInput');

imageUploadArea.addEventListener('click', () => imageInput.click());
imageUploadArea.addEventListener('dragover', e => { e.preventDefault(); });
imageUploadArea.addEventListener('drop', e => {
  e.preventDefault();
  if (e.dataTransfer.files.length) {
    imageInput.files = e.dataTransfer.files;
    previewImage(e.dataTransfer.files[0]);
  }
});
imageInput.addEventListener('change', () => {
  if (imageInput.files.length) previewImage(imageInput.files[0]);
});

function previewImage(file) {
  const reader = new FileReader();
  reader.onload = e => {
    const preview = document.getElementById('imagePreview');
    preview.src = e.target.result;
    preview.style.display = 'block';
  };
  reader.readAsDataURL(file);
}

/* ── Comments ───────────────────────────────────── */
async function loadComments(taskId) {
  const comments = await api(`/api/tasks/${taskId}/comments`);
  const list = document.getElementById('commentsList');
  if (!comments.length) {
    list.innerHTML = '<div style="color:var(--text-muted);font-size:13px;padding:8px 0">No comments yet</div>';
    return;
  }
  list.innerHTML = comments.map(c => {
    const content = c.content.replace(/@(\S+)/g, '<span class="mention">@$1</span>');
    return `
      <div class="comment">
        <span class="comment-author">${escHtml(c.author?.nickname || 'Unknown')}</span>
        <span class="comment-time">${timeAgo(c.created_at)}</span>
        <div class="comment-content">${content}</div>
      </div>
    `;
  }).join('');
}

document.getElementById('addCommentBtn').addEventListener('click', async () => {
  const input = document.getElementById('commentInput');
  const content = input.value.trim();
  if (!content) return;
  const taskId = document.getElementById('taskId').value;
  if (!taskId) return;

  await api(`/api/tasks/${taskId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ content, author_id: currentUser.id }),
  });
  input.value = '';
  await loadComments(taskId);
  pollNotifications();
});

document.getElementById('commentInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    document.getElementById('addCommentBtn').click();
  }
});

/* ── Mention Autocomplete ───────────────────────── */
const commentInput = document.getElementById('commentInput');
const mentionDropdown = document.getElementById('mentionDropdown');
let mentionStart = -1;

commentInput.addEventListener('input', () => {
  const val = commentInput.value;
  const cursor = commentInput.selectionStart;
  const beforeCursor = val.substring(0, cursor);
  const atMatch = beforeCursor.match(/@(\S*)$/);

  if (atMatch) {
    mentionStart = atMatch.index;
    const query = atMatch[1].toLowerCase();
    const matches = allUsers.filter(u =>
      u.nickname.toLowerCase().includes(query) && u.id !== currentUser.id
    );
    if (matches.length > 0) {
      mentionDropdown.innerHTML = matches.map(u =>
        `<div class="mention-option" data-nickname="${escHtml(u.nickname)}">${escHtml(u.nickname)}</div>`
      ).join('');
      mentionDropdown.classList.add('active');

      mentionDropdown.querySelectorAll('.mention-option').forEach(opt => {
        opt.addEventListener('click', () => {
          const before = val.substring(0, mentionStart);
          const after = val.substring(cursor);
          commentInput.value = before + '@' + opt.dataset.nickname + ' ' + after;
          mentionDropdown.classList.remove('active');
          commentInput.focus();
        });
      });
      return;
    }
  }
  mentionDropdown.classList.remove('active');
});

/* ── Utilities ──────────────────────────────────── */
function escHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function parseTags(tagsStr) {
  if (!tagsStr) return [];
  try { return JSON.parse(tagsStr); } catch { return []; }
}

function renderDueDate(dateStr) {
  const due = new Date(dateStr);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const diff = (due - now) / (1000 * 60 * 60 * 24);
  let cls = 'due-date';
  if (diff < 0) cls += ' overdue';
  else if (diff <= 2) cls += ' soon';
  const formatted = dateStr;
  return `<span class="${cls}">${formatted}</span>`;
}

function timeAgo(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/* ── Close panels on outside click ──────────────── */
document.addEventListener('click', e => {
  const bell = document.getElementById('notifBell');
  const panel = document.getElementById('notifPanel');
  if (notifPanelOpen && !bell.contains(e.target) && !panel.contains(e.target)) {
    notifPanelOpen = false;
    panel.classList.remove('active');
  }
});
