"use strict";

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

function getApiBaseUrl() {
  const meta = document.querySelector('meta[name="api-base-url"]');
  const value = meta ? meta.content.trim() : "";
  // Falls back to same-origin if unset or not substituted (e.g. local file:// testing).
  if (!value || value.includes("${")) return "";
  return value.replace(/\/$/, "");
}

const API_BASE_URL = getApiBaseUrl();

function getInitData() {
  if (tg && tg.initData) return tg.initData;
  // Fallback for local browser testing (no real Telegram client):
  // open index.html as /?initData=<urlencoded initData from a test script>.
  const params = new URLSearchParams(window.location.search);
  return params.get("initData") || "";
}

const INIT_DATA = getInitData();

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}/api${path}`, {
    ...options,
    headers: {
      "X-Telegram-Init-Data": INIT_DATA,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : null;
  if (!res.ok) {
    const detail = body && body.detail;
    throw new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
  }
  return body;
}

function setMessage(el, text, isError = false) {
  el.textContent = text || "";
  el.classList.toggle("error", Boolean(isError));
}

function formatSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(1)} ${units[i]}`;
}

// ── Tabs ─────────────────────────────────────────────────────────────────

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ── Modal ────────────────────────────────────────────────────────────────

const modalOverlay = document.getElementById("modal-overlay");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");
const modalClose = document.getElementById("modal-close");

function showModal(title, bodyNode) {
  modalTitle.textContent = title;
  modalBody.innerHTML = "";
  modalBody.appendChild(bodyNode);
  modalOverlay.classList.remove("hidden");
}

function hideModal() {
  modalOverlay.classList.add("hidden");
}

modalClose.addEventListener("click", hideModal);

// ── Queue ────────────────────────────────────────────────────────────────

const queueForm = document.getElementById("queue-form");
const queueUrlInput = document.getElementById("queue-url");
const queueNameInput = document.getElementById("queue-name");
const queueMessage = document.getElementById("queue-message");
const queueList = document.getElementById("queue-list");

function renderQueue(entries) {
  queueList.innerHTML = "";
  if (!entries.length) {
    queueList.innerHTML = '<li class="list-item-sub">Queue is empty.</li>';
    return;
  }
  for (const entry of entries) {
    const pct = entry.bytes_total
      ? Math.round((entry.bytes_loaded / entry.bytes_total) * 100)
      : 0;
    const li = document.createElement("li");
    li.className = "list-item";
    li.innerHTML = `
      <div class="list-item-header">
        <span class="list-item-name">${entry.name}</span>
        <button class="list-item-remove" data-name="${entry.name}" type="button">Remove</button>
      </div>
      <div class="list-item-sub">${entry.status}${entry.url ? " — " + entry.url : ""}</div>
      <div class="progress-bar"><div class="progress-bar-fill" style="width:${pct}%"></div></div>
      <div class="list-item-sub">${pct}% — ${formatSize(entry.bytes_loaded)} / ${formatSize(entry.bytes_total)}</div>
    `;
    queueList.appendChild(li);
  }
  queueList.querySelectorAll(".list-item-remove").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await apiFetch(`/queue/${encodeURIComponent(btn.dataset.name)}`, { method: "DELETE" });
        await refreshQueue();
      } catch (err) {
        setMessage(queueMessage, err.message, true);
      }
    });
  });
}

async function refreshQueue() {
  try {
    const entries = await apiFetch("/queue");
    renderQueue(entries);
  } catch (err) {
    setMessage(queueMessage, err.message, true);
  }
}

function showOptionsModal(packageUuid, finalName, options) {
  const container = document.createElement("div");
  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.className = "modal-option";
    btn.type = "button";
    btn.textContent = opt.label;
    btn.addEventListener("click", async () => {
      hideModal();
      try {
        await apiFetch(`/queue/${packageUuid}/select`, {
          method: "POST",
          body: JSON.stringify({
            link_uuid: opt.link_uuid,
            variant_id: opt.variant_id,
            final_name: finalName,
          }),
        });
        setMessage(queueMessage, `Queued: ${finalName}`);
        await refreshQueue();
      } catch (err) {
        setMessage(queueMessage, err.message, true);
      }
    });
    container.appendChild(btn);
  });
  showModal("Choose a file/quality", container);
}

function showDuplicateModal(url, name, existing) {
  const container = document.createElement("div");
  const info = document.createElement("p");
  const matched = existing.matched_by === "url" ? "URL" : "file name";
  info.textContent =
    `This ${matched} was already queued on ${existing.added_at} as "${existing.package_name}".`;
  container.appendChild(info);

  const redownloadBtn = document.createElement("button");
  redownloadBtn.className = "modal-option";
  redownloadBtn.type = "button";
  redownloadBtn.textContent = "Download again";
  redownloadBtn.addEventListener("click", async () => {
    hideModal();
    await submitQueue(url, name, true);
  });
  container.appendChild(redownloadBtn);

  if (existing.file_path) {
    const downloadLink = document.createElement("a");
    downloadLink.className = "modal-option";
    downloadLink.textContent = "Download existing file";
    downloadLink.href = `${API_BASE_URL}/api/queue/${encodeURIComponent(existing.package_name)}/file`;
    downloadLink.addEventListener("click", hideModal);
    container.appendChild(downloadLink);
  }

  showModal("Already queued", container);
}

async function submitQueue(url, name, force) {
  try {
    const result = await apiFetch("/queue", {
      method: "POST",
      body: JSON.stringify({ url, name: name || null, force }),
    });
    if (result.status === "duplicate") {
      showDuplicateModal(url, name, result.existing);
      return;
    }
    if (result.status === "choose_option") {
      showOptionsModal(result.package_uuid, result.final_name, result.options);
      return;
    }
    setMessage(queueMessage, `Queued: ${result.final_name}`);
    await refreshQueue();
  } catch (err) {
    setMessage(queueMessage, err.message, true);
  }
}

queueForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(queueMessage, "");
  const url = queueUrlInput.value.trim();
  const name = queueNameInput.value.trim();
  await submitQueue(url, name, false);
  queueUrlInput.value = "";
  queueNameInput.value = "";
});

// ── Accounts ─────────────────────────────────────────────────────────────

const accountForm = document.getElementById("account-form");
const hosterInput = document.getElementById("account-hoster");
const usernameInput = document.getElementById("account-username");
const passwordInput = document.getElementById("account-password");
const accountMessage = document.getElementById("account-message");
const accountList = document.getElementById("account-list");

function renderAccounts(accounts) {
  accountList.innerHTML = "";
  if (!accounts.length) {
    accountList.innerHTML = '<li class="list-item-sub">No premium accounts configured.</li>';
    return;
  }
  for (const acc of accounts) {
    const li = document.createElement("li");
    li.className = "list-item";
    const status = acc.valid ? "✅" : "⚠️";
    li.innerHTML = `
      <div class="list-item-header">
        <span class="list-item-name">${status} ${acc.hostname || "?"}</span>
        <button class="list-item-remove" data-id="${acc.uuid}" type="button">Remove</button>
      </div>
      <div class="list-item-sub">${acc.userName || "?"}</div>
    `;
    accountList.appendChild(li);
  }
  accountList.querySelectorAll(".list-item-remove").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await apiFetch(`/accounts/${btn.dataset.id}`, { method: "DELETE" });
        await refreshAccounts();
      } catch (err) {
        setMessage(accountMessage, err.message, true);
      }
    });
  });
}

async function refreshAccounts() {
  try {
    const accounts = await apiFetch("/accounts");
    renderAccounts(accounts);
  } catch (err) {
    setMessage(accountMessage, err.message, true);
  }
}

accountForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(accountMessage, "");
  try {
    await apiFetch("/accounts", {
      method: "POST",
      body: JSON.stringify({
        hoster: hosterInput.value.trim(),
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });
    accountForm.reset();
    setMessage(accountMessage, "Account added.");
    await refreshAccounts();
  } catch (err) {
    setMessage(accountMessage, err.message, true);
  }
});

// ── Init ─────────────────────────────────────────────────────────────────

refreshQueue();
refreshAccounts();
setInterval(refreshQueue, 3000);
