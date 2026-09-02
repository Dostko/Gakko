const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const stage = document.getElementById("chatStage");
const sendButton = document.getElementById("sendButton");
const attachButton = document.getElementById("attachButton");
const statusNote = document.getElementById("statusNote");
const attachmentStrip = document.createElement("div");
attachmentStrip.hidden = true;
attachmentStrip.style.display = "flex";
attachmentStrip.style.flexWrap = "wrap";
attachmentStrip.style.gap = "7px";
attachmentStrip.style.marginBottom = "8px";
attachmentStrip.style.padding = "0 4px";
form.insertAdjacentElement("beforebegin", attachmentStrip);
const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.getElementById("sidebarToggle");
const chatButton = document.getElementById("chatButton");
const historyButton = document.getElementById("historyButton");
const composerArea = document.querySelector(".composer-area");
const historyView = document.getElementById("historyView");
const historySearch = document.getElementById("historySearch");
const historyList = document.getElementById("historyList");
const historyDetail = document.getElementById("historyDetail");
const historyDeleteBefore = document.getElementById("historyDeleteBefore");
const historyDeleteBeforeButton = document.getElementById("historyDeleteBeforeButton");
const historyRetentionNote = document.getElementById("historyRetentionNote");
const projectButton = document.getElementById("projectButton");
const projectMenu = document.getElementById("projectMenu");
const newProjectButton = document.getElementById("newProjectButton");
const openProjectButton = document.getElementById("openProjectButton");
const activeProject = document.getElementById("activeProject");
const activeProjectName = document.getElementById("activeProjectName");
const activeProjectPath = document.getElementById("activeProjectPath");
const projectTree = document.getElementById("projectTree");
const projectTreeList = document.getElementById("projectTreeList");
const sidebarResizer = document.getElementById("sidebarResizer");
const timerPanel = document.createElement("div");
timerPanel.style.display = "grid";
timerPanel.style.gridTemplateColumns = "1fr auto 1fr";
timerPanel.style.alignItems = "center";
timerPanel.style.gap = "12px";
timerPanel.style.marginTop = "8px";

const timerDisplay = document.createElement("span");
timerDisplay.textContent = "00:00.0";
timerDisplay.style.fontSize = "10px";
timerDisplay.style.fontWeight = "600";
timerDisplay.style.fontVariantNumeric = "tabular-nums";
timerDisplay.style.letterSpacing = "0.5px";
timerDisplay.style.justifySelf = "start";

const shortcutNote = document.createElement("span");
shortcutNote.textContent = "Ctrl+Shift · Alt satır";
shortcutNote.style.fontSize = "10px";
shortcutNote.style.justifySelf = "end";

statusNote.insertAdjacentElement("afterend", timerPanel);
timerPanel.appendChild(timerDisplay);
timerPanel.appendChild(statusNote);
timerPanel.appendChild(shortcutNote);
statusNote.style.justifySelf = "center";

let bridge = null;
let waiting = false;
let timerStartedAt = null;
let timerInterval = null;
let sidebarOpenWidth = 180;
let resizingSidebar = false;
let currentView = "chat";
let selectedHistoryId = null;
let historySearchTimer = null;
let selectedChatFiles = [];
const projectDirectoryCache = new Map();
const expandedProjectDirectories = new Set();

const SIDEBAR_MIN_WIDTH = 150;
const SIDEBAR_MAX_WIDTH = 520;

function attachmentDisplayText(text) {
  const cleanText = String(text || "").trim();
  const base = cleanText || "Ekli dosyaları incele.";
  if (selectedChatFiles.length === 0) {
    return base;
  }
  const names = selectedChatFiles.map(file => String(file.name || "dosya"));
  return `${base}

Ekler: ${names.join(", ")}`;
}

function renderAttachmentStrip() {
  attachmentStrip.replaceChildren();
  attachmentStrip.hidden = selectedChatFiles.length === 0;

  selectedChatFiles.forEach(file => {
    const chip = document.createElement("div");
    chip.style.display = "inline-flex";
    chip.style.alignItems = "center";
    chip.style.gap = "7px";
    chip.style.maxWidth = "280px";
    chip.style.minHeight = "30px";
    chip.style.padding = "0 8px 0 10px";
    chip.style.border = "1px solid #253142";
    chip.style.borderRadius = "9px";
    chip.style.background = "#0d121b";
    chip.style.color = "#dfe7f0";
    chip.style.fontSize = "12px";
    chip.title = String(file.path || "");

    const icon = document.createElement("span");
    icon.textContent = file.type === "image" ? "▧" : "▤";
    icon.style.color = file.type === "image" ? "#6fb7ff" : "#aeb6c4";

    const name = document.createElement("span");
    name.textContent = String(file.name || "dosya");
    name.style.overflow = "hidden";
    name.style.textOverflow = "ellipsis";
    name.style.whiteSpace = "nowrap";

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.title = "Eki kaldır";
    remove.style.border = "0";
    remove.style.background = "transparent";
    remove.style.color = "#8f9bad";
    remove.style.cursor = "pointer";
    remove.style.fontSize = "16px";
    remove.style.lineHeight = "1";
    remove.style.padding = "0 2px";
    remove.addEventListener("click", () => {
      selectedChatFiles = selectedChatFiles.filter(
        current => String(current.path || "") !== String(file.path || "")
      );
      renderAttachmentStrip();
      input.focus();
    });

    chip.appendChild(icon);
    chip.appendChild(name);
    chip.appendChild(remove);
    attachmentStrip.appendChild(chip);
  });
}

function mergeSelectedChatFiles(files) {
  const byPath = new Map(
    selectedChatFiles.map(file => [String(file.path || "").toLowerCase(), file])
  );

  (Array.isArray(files) ? files : []).forEach(file => {
    const path = String(file.path || "").trim();
    if (!path) {
      return;
    }
    byPath.set(path.toLowerCase(), {
      path,
      name: String(file.name || path.split(/[\\/]/).pop() || "dosya"),
      type: file.type === "image" ? "image" : "file"
    });
  });

  selectedChatFiles = Array.from(byPath.values());
  renderAttachmentStrip();
}

function clampSidebarWidth(width) {
  const viewportLimit = Math.max(SIDEBAR_MIN_WIDTH, Math.floor(window.innerWidth * 0.55));
  return Math.max(
    SIDEBAR_MIN_WIDTH,
    Math.min(Number(width) || 180, SIDEBAR_MAX_WIDTH, viewportLimit)
  );
}

function applySidebarWidth(width) {
  sidebarOpenWidth = clampSidebarWidth(width);
  appShell.style.setProperty("--sidebar-open-width", `${sidebarOpenWidth}px`);
}

function requestProjectDirectory(relativePath = "") {
  if (!bridge || typeof bridge.list_project_directory !== "function") {
    return;
  }

  bridge.list_project_directory(String(relativePath || ""));
}

function refreshVisibleProjectDirectories() {
  if (!activeProject.hidden) {
    requestProjectDirectory("");
    expandedProjectDirectories.forEach(path => requestProjectDirectory(path));
  }
}

function createProjectTreeRow(entry, depth) {
  const row = document.createElement(entry.type === "directory" ? "button" : "div");
  row.className = `project-tree-item ${entry.type}`;
  row.style.paddingLeft = `${8 + depth * 14}px`;
  row.title = entry.path;

  const marker = document.createElement("span");
  marker.className = "project-tree-marker";

  if (entry.type === "directory") {
    const opened = expandedProjectDirectories.has(entry.path);
    marker.textContent = opened ? "⌄" : "›";
  } else {
    marker.textContent = "·";
  }

  const label = document.createElement("span");
  label.className = "project-tree-name";
  label.textContent = entry.name;

  row.appendChild(marker);
  row.appendChild(label);

  if (entry.type === "directory") {
    row.type = "button";
    row.addEventListener("click", () => {
      if (expandedProjectDirectories.has(entry.path)) {
        expandedProjectDirectories.delete(entry.path);
        renderProjectTree();
        return;
      }

      expandedProjectDirectories.add(entry.path);
      if (!projectDirectoryCache.has(entry.path)) {
        requestProjectDirectory(entry.path);
      }
      renderProjectTree();
    });
  }

  return row;
}

function appendProjectTreeBranch(container, relativePath, depth) {
  const payload = projectDirectoryCache.get(relativePath);
  if (!payload) {
    return;
  }

  payload.entries.forEach(entry => {
    container.appendChild(createProjectTreeRow(entry, depth));

    if (
      entry.type === "directory"
      && expandedProjectDirectories.has(entry.path)
      && projectDirectoryCache.has(entry.path)
    ) {
      appendProjectTreeBranch(container, entry.path, depth + 1);
    }
  });
}

function renderProjectTree() {
  projectTreeList.replaceChildren();
  const rootPayload = projectDirectoryCache.get("");

  if (!rootPayload) {
    projectTree.hidden = true;
    return;
  }

  projectTree.hidden = false;

  if (rootPayload.entries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "project-tree-empty";
    empty.textContent = "Henüz dosya yok";
    projectTreeList.appendChild(empty);
    return;
  }

  appendProjectTreeBranch(projectTreeList, "", 0);
}

function resetProjectTree() {
  projectDirectoryCache.clear();
  expandedProjectDirectories.clear();
  projectTreeList.replaceChildren();
  projectTree.hidden = true;
}

function formatElapsed(milliseconds) {
  const totalTenths = Math.max(0, Math.floor(milliseconds / 100));
  const minutes = Math.floor(totalTenths / 600);
  const seconds = Math.floor((totalTenths % 600) / 10);
  const tenths = totalTenths % 10;

  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${tenths}`;
}

function renderTimer() {
  if (timerStartedAt === null) {
    return;
  }

  timerDisplay.textContent = formatElapsed(performance.now() - timerStartedAt);
}

function startTimer() {
  if (timerInterval !== null) {
    clearInterval(timerInterval);
  }

  timerStartedAt = performance.now();
  timerDisplay.textContent = "00:00.0";
  renderTimer();
  timerInterval = setInterval(renderTimer, 100);
}

function stopTimer() {
  if (timerStartedAt === null) {
    return;
  }

  timerDisplay.textContent = formatElapsed(performance.now() - timerStartedAt);

  if (timerInterval !== null) {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  timerStartedAt = null;
}

function resize() {
  input.style.height = "40px";
  input.style.height = Math.max(40, Math.min(input.scrollHeight, 170)) + "px";
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeCodeLanguage(language, code) {
  const raw = String(language || "").trim().toLowerCase();
  const aliases = {
    js: "JavaScript",
    javascript: "JavaScript",
    ts: "TypeScript",
    typescript: "TypeScript",
    py: "Python",
    python: "Python",
    html: "HTML",
    htm: "HTML",
    css: "CSS",
    json: "JSON",
    bash: "Bash",
    sh: "Bash",
    shell: "Bash",
    powershell: "PowerShell",
    ps1: "PowerShell",
    text: "Metin",
    txt: "Metin"
  };

  if (aliases[raw]) {
    return aliases[raw];
  }

  if (raw) {
    return raw.toUpperCase();
  }

  const sample = String(code || "").trim();
  if (/^(?:<!doctype\s+html|<html\b|<[a-z][\s\S]*>)/i.test(sample)) {
    return "HTML";
  }
  if (/\b(?:const|let|var|function|=>|document\.)\b/.test(sample)) {
    return "JavaScript";
  }
  if (/^(?:from\s+\S+\s+import|import\s+\S+|def\s+\w+|class\s+\w+)/m.test(sample)) {
    return "Python";
  }
  if (/^[.#]?[\w-]+[^\n{]*\{[\s\S]*:[^;{}]+;?/m.test(sample)) {
    return "CSS";
  }
  return "Kod";
}

function highlightCode(code, language) {
  const source = String(code || "");
  const displayLanguage = normalizeCodeLanguage(language, source);
  const keywordPattern = /\b(?:async|await|break|case|catch|class|const|continue|def|del|do|elif|else|except|export|extends|false|finally|for|from|function|if|import|in|interface|let|new|null|pass|return|switch|throw|true|try|var|while|with|yield|None|True|False)\b/;
  const tokenPattern = /(<!--[\s\S]*?-->|\/\*[\s\S]*?\*\/|\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|<\/?[A-Za-z][^>]*>|#[0-9a-fA-F]{3,8}\b|\b\d+(?:\.\d+)?\b|\b(?:async|await|break|case|catch|class|const|continue|def|del|do|elif|else|except|export|extends|false|finally|for|from|function|if|import|in|interface|let|new|null|pass|return|switch|throw|true|try|var|while|with|yield|None|True|False)\b)/g;

  let html = "";
  let cursor = 0;

  source.replace(tokenPattern, (token, _match, offset) => {
    html += escapeHtml(source.slice(cursor, offset));

    let className = "";
    if (/^(?:<!--|\/\*|\/\/|#(?![0-9a-fA-F]{3,8}\b))/.test(token)) {
      className = "syn-comment";
    } else if (/^["'`]/.test(token)) {
      className = "syn-string";
    } else if (/^<\/?[A-Za-z]/.test(token)) {
      className = "syn-tag";
    } else if (/^#[0-9a-fA-F]{3,8}\b/.test(token) || /^\d/.test(token)) {
      className = "syn-number";
    } else if (keywordPattern.test(token)) {
      className = "syn-keyword";
    }

    html += className
      ? `<span class="${className}">${escapeHtml(token)}</span>`
      : escapeHtml(token);
    cursor = offset + token.length;
    return token;
  });

  html += escapeHtml(source.slice(cursor));
  return { html, displayLanguage };
}

async function copyCodeText(codeText, button) {
  let copied = false;

  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(codeText);
      copied = true;
    }
  } catch (error) {
    copied = false;
  }

  if (!copied) {
    const helper = document.createElement("textarea");
    helper.value = codeText;
    helper.setAttribute("readonly", "");
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.appendChild(helper);
    helper.select();
    copied = document.execCommand("copy");
    helper.remove();
  }

  const oldText = button.textContent;
  button.textContent = copied ? "Kopyalandı" : "Kopyalanamadı";
  setTimeout(() => {
    button.textContent = oldText;
  }, 1400);
}

function createCodeBlock(codeText, language) {
  const wrapper = document.createElement("div");
  wrapper.className = "code-block";

  const header = document.createElement("div");
  header.className = "code-block-header";

  const highlighted = highlightCode(codeText, language);
  const languageLabel = document.createElement("span");
  languageLabel.className = "code-language";
  languageLabel.textContent = highlighted.displayLanguage;

  const copyButton = document.createElement("button");
  copyButton.className = "code-copy-button";
  copyButton.type = "button";
  copyButton.textContent = "Kopyala";
  copyButton.addEventListener("click", () => copyCodeText(codeText, copyButton));

  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.innerHTML = highlighted.html;
  pre.appendChild(code);

  header.appendChild(languageLabel);
  header.appendChild(copyButton);
  wrapper.appendChild(header);
  wrapper.appendChild(pre);
  return wrapper;
}

function appendPlainAssistantText(container, text) {
  if (!text) {
    return;
  }

  const part = document.createElement("span");
  part.className = "message-text";
  part.textContent = text;
  container.appendChild(part);
}

function renderAssistantContent(container, text) {
  const source = String(text || "");
  const fencePattern = /```([^\n`]*)\n([\s\S]*?)```/g;
  let cursor = 0;
  let match = null;

  while ((match = fencePattern.exec(source)) !== null) {
    appendPlainAssistantText(container, source.slice(cursor, match.index));
    container.appendChild(createCodeBlock(match[2].replace(/\n$/, ""), match[1]));
    cursor = match.index + match[0].length;
  }

  appendPlainAssistantText(container, source.slice(cursor));
}

function addMessage(text, role) {
  const el = document.createElement("div");
  el.className = "message " + role;

  if (role === "assistant") {
    renderAssistantContent(el, text);
  } else {
    el.textContent = String(text || "");
  }

  messages.appendChild(el);
  welcome.classList.add("hidden");

  stage.scrollTo({
    top: stage.scrollHeight,
    behavior: "smooth"
  });
}

function setWaiting(value) {
  waiting = Boolean(value);
  sendButton.disabled = waiting;
  attachButton.disabled = waiting;
  input.disabled = waiting;

  statusNote.textContent = waiting
    ? "Gakko düşünüyor..."
    : "Gakko AI";

  if (!waiting) {
    input.focus();
  }
}

function showActiveProject(path, startsProjectMethod) {
  const projectPath = String(path || "").trim();
  if (!projectPath) {
    return;
  }

  const cleanPath = projectPath.replace(/[\\/]+$/, "");
  const parts = cleanPath.split(/[\\/]/);

  activeProjectName.textContent = parts[parts.length - 1] || cleanPath;
  activeProjectPath.textContent = projectPath;
  activeProject.hidden = false;
  resetProjectTree();
  requestProjectDirectory("");
  projectMenu.hidden = false;
  projectButton.setAttribute("aria-expanded", "true");

  if (startsProjectMethod) {
    setWaiting(true);
    startTimer();
  }

  appShell.classList.add("sidebar-open");
  sidebarToggle.setAttribute("aria-expanded", "true");
  sidebarToggle.title = "Menüyü kapat";
}

function formatHistoryDate(value) {
  const date = new Date(String(value || ""));
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function setMainView(view) {
  currentView = view === "history" ? "history" : "chat";
  const historyOpen = currentView === "history";

  historyView.hidden = !historyOpen;
  stage.hidden = historyOpen;
  composerArea.hidden = historyOpen;
  historyButton.classList.toggle("active", historyOpen);
  chatButton.classList.toggle("active", !historyOpen);

  if (!historyOpen) {
    input.focus();
  }
}

function requestHistory(query = historySearch.value) {
  if (!bridge || typeof bridge.list_history !== "function") {
    statusNote.textContent = "Geçmiş bağlantısı henüz hazır değil";
    return;
  }
  bridge.list_history(String(query || ""));
}

function clearHistoryDetail(message = "Okumak için soldan bir sohbet seç.") {
  selectedHistoryId = null;
  historyDetail.replaceChildren();
  const empty = document.createElement("div");
  empty.className = "history-empty";
  empty.textContent = message;
  historyDetail.appendChild(empty);
}

function renderHistorySessions(payload) {
  const sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
  const retentionDays = Number(payload.retention_days) || 30;
  historyRetentionNote.textContent = `Son ${retentionDays} günlük sohbet geçmişi`;
  historyList.replaceChildren();

  if (sessions.length === 0) {
    const empty = document.createElement("div");
    empty.className = "history-empty";
    empty.textContent = historySearch.value.trim()
      ? "Aramayla eşleşen sohbet bulunamadı."
      : "Henüz kaydedilmiş sohbet yok.";
    historyList.appendChild(empty);
    clearHistoryDetail();
    return;
  }

  const existingIds = new Set(sessions.map(session => String(session.id || "")));
  if (selectedHistoryId && !existingIds.has(selectedHistoryId)) {
    clearHistoryDetail();
  }

  sessions.forEach(session => {
    const id = String(session.id || "");
    const item = document.createElement("button");
    item.type = "button";
    item.className = "history-item";
    if (id === selectedHistoryId) {
      item.classList.add("active");
    }

    const title = document.createElement("strong");
    title.textContent = String(session.title || "Sohbet");

    const meta = document.createElement("div");
    meta.className = "history-item-meta";
    const parts = [formatHistoryDate(session.updated_at)];
    if (session.project_name) {
      parts.push(String(session.project_name));
    }
    parts.push(`${Number(session.message_count) || 0} mesaj`);
    meta.textContent = parts.filter(Boolean).join(" · ");

    item.appendChild(title);
    item.appendChild(meta);
    item.addEventListener("click", () => {
      selectedHistoryId = id;
      if (bridge && typeof bridge.get_history_session === "function") {
        bridge.get_history_session(id);
      }
      renderHistorySessions(payload);
    });
    historyList.appendChild(item);
  });
}

function renderHistorySession(session) {
  if (!session || !session.id) {
    clearHistoryDetail("Bu sohbet artık bulunamıyor.");
    return;
  }

  selectedHistoryId = String(session.id);
  historyDetail.replaceChildren();

  const head = document.createElement("div");
  head.className = "history-detail-head";

  const info = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = String(session.title || "Sohbet");
  const meta = document.createElement("div");
  meta.className = "history-detail-meta";
  const metaParts = [formatHistoryDate(session.updated_at)];
  if (session.project_name) {
    metaParts.push(String(session.project_name));
  }
  meta.textContent = metaParts.filter(Boolean).join(" · ");
  info.appendChild(title);
  info.appendChild(meta);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "history-delete-one";
  deleteButton.textContent = "Sohbeti sil";
  deleteButton.addEventListener("click", () => {
    if (!confirm("Bu sohbet geçmişten kalıcı olarak silinsin mi?")) {
      return;
    }
    if (bridge && typeof bridge.delete_history_session === "function") {
      bridge.delete_history_session(String(session.id));
    }
  });

  head.appendChild(info);
  head.appendChild(deleteButton);
  historyDetail.appendChild(head);

  const historyMessages = document.createElement("div");
  historyMessages.className = "history-messages";

  (Array.isArray(session.messages) ? session.messages : []).forEach(message => {
    const role = message.role === "user" ? "user" : "assistant";
    const item = document.createElement("div");
    item.className = `history-message ${role}`;
    if (role === "assistant") {
      renderAssistantContent(item, message.content);
    } else {
      item.textContent = String(message.content || "");
    }
    historyMessages.appendChild(item);
  });

  historyDetail.appendChild(historyMessages);
}

function connectBridge() {
  if (typeof QWebChannel === "undefined" || !window.qt || !qt.webChannelTransport) {
    statusNote.textContent = "Qwen bağlantısı kurulamadı";
    return;
  }

  new QWebChannel(qt.webChannelTransport, channel => {
    bridge = channel.objects.gakkoBridge;

    bridge.project_selected.connect(path => {
      showActiveProject(path, true);
    });

    if (typeof bridge.get_active_project === "function") {
      bridge.get_active_project(projectPath => {
        showActiveProject(projectPath, false);
      });
    }

    bridge.project_directory_ready.connect(payloadText => {
      try {
        const payload = JSON.parse(String(payloadText || "{}"));
        const path = String(payload.path || "");
        const entries = Array.isArray(payload.entries) ? payload.entries : [];
        projectDirectoryCache.set(path, { path, entries });
        renderProjectTree();
      } catch (error) {
        statusNote.textContent = "Proje dosya ağacı okunamadı";
      }
    });

    bridge.history_sessions_ready.connect(payloadText => {
      try {
        renderHistorySessions(JSON.parse(String(payloadText || "{}")));
      } catch (error) {
        statusNote.textContent = "Sohbet geçmişi okunamadı";
      }
    });

    bridge.history_session_ready.connect(payloadText => {
      try {
        renderHistorySession(JSON.parse(String(payloadText || "{}")));
      } catch (error) {
        statusNote.textContent = "Sohbet geçmişi açılamadı";
      }
    });

    bridge.history_action_ready.connect(payloadText => {
      try {
        const payload = JSON.parse(String(payloadText || "{}"));
        const deleted = Number(payload.deleted) || 0;
        statusNote.textContent = deleted > 0
          ? `${deleted} geçmiş kaydı silindi`
          : "Silinecek geçmiş kaydı bulunamadı";
        clearHistoryDetail();
      } catch (error) {
        statusNote.textContent = "Geçmiş işlemi tamamlanamadı";
      }
    });

    bridge.chat_files_selected.connect(payloadText => {
      try {
        const payload = JSON.parse(String(payloadText || "{}"));
        mergeSelectedChatFiles(payload.files);
        statusNote.textContent = "Ekler hazır";
        input.focus();
      } catch (error) {
        statusNote.textContent = "Ekli dosyalar alınamadı";
      }
    });

    bridge.reply_ready.connect(reply => {
      addMessage(reply, "assistant");
      setWaiting(false);
      stopTimer();
      refreshVisibleProjectDirectories();
    });

    bridge.error_ready.connect(error => {
      addMessage("Hata: " + error, "assistant");
      setWaiting(false);
      stopTimer();
    });

    statusNote.textContent = "Gakko AI";
  });
}

function closeProjectMenu() {
  projectMenu.hidden = true;
  projectButton.setAttribute("aria-expanded", "false");
}

function setSidebarOpen(opened) {
  appShell.classList.toggle("sidebar-open", opened);
  sidebarToggle.setAttribute("aria-expanded", String(opened));
  sidebarToggle.title = opened
    ? "Menüyü kapat"
    : "Menüyü aç";

  if (!opened) {
    closeProjectMenu();
  }
}

sidebarToggle.addEventListener("click", () => {
  setSidebarOpen(!appShell.classList.contains("sidebar-open"));
});

chatButton.addEventListener("click", () => {
  setMainView("chat");
});

historyButton.addEventListener("click", () => {
  setMainView("history");
  requestHistory();
});

historySearch.addEventListener("input", () => {
  if (historySearchTimer !== null) {
    clearTimeout(historySearchTimer);
  }
  historySearchTimer = setTimeout(() => requestHistory(), 180);
});

historyDeleteBeforeButton.addEventListener("click", () => {
  const value = String(historyDeleteBefore.value || "").trim();
  if (!value) {
    statusNote.textContent = "Önce bir tarih seç";
    return;
  }

  const cutoff = new Date(`${value}T00:00:00`);
  if (Number.isNaN(cutoff.getTime())) {
    statusNote.textContent = "Geçerli bir tarih seç";
    return;
  }

  if (!confirm(`${value} tarihinden önceki sohbetler kalıcı olarak silinsin mi?`)) {
    return;
  }

  if (bridge && typeof bridge.delete_history_before === "function") {
    bridge.delete_history_before(cutoff.toISOString());
  }
});

projectButton.addEventListener("click", () => {
  if (!appShell.classList.contains("sidebar-open")) {
    setSidebarOpen(true);
  }

  const opened = projectMenu.hidden;
  projectMenu.hidden = !opened;
  projectButton.setAttribute("aria-expanded", String(opened));
});

newProjectButton.addEventListener("click", () => {
  closeProjectMenu();

  if (!bridge || typeof bridge.start_new_project !== "function") {
    statusNote.textContent = "Yeni proje bağlantısı henüz hazır değil";
    return;
  }

  bridge.start_new_project();
});

openProjectButton.addEventListener("click", () => {
  closeProjectMenu();

  if (!bridge || typeof bridge.select_project_folder !== "function") {
    statusNote.textContent = "Proje seçici henüz hazır değil";
    return;
  }

  bridge.select_project_folder();
});

attachButton.addEventListener("click", () => {
  if (waiting) {
    return;
  }

  if (!bridge || typeof bridge.select_chat_files !== "function") {
    statusNote.textContent = "Dosya seçici henüz hazır değil";
    return;
  }

  bridge.select_chat_files();
});

sidebarResizer.addEventListener("pointerdown", event => {
  if (!appShell.classList.contains("sidebar-open")) {
    return;
  }

  event.preventDefault();
  resizingSidebar = true;
  appShell.classList.add("sidebar-resizing");
  sidebarResizer.setPointerCapture(event.pointerId);
});

sidebarResizer.addEventListener("pointermove", event => {
  if (!resizingSidebar) {
    return;
  }

  const shellLeft = appShell.getBoundingClientRect().left;
  applySidebarWidth(event.clientX - shellLeft);
});

function finishSidebarResize(event) {
  if (!resizingSidebar) {
    return;
  }

  resizingSidebar = false;
  appShell.classList.remove("sidebar-resizing");

  if (sidebarResizer.hasPointerCapture(event.pointerId)) {
    sidebarResizer.releasePointerCapture(event.pointerId);
  }
}

sidebarResizer.addEventListener("pointerup", finishSidebarResize);
sidebarResizer.addEventListener("pointercancel", finishSidebarResize);

window.addEventListener("resize", () => {
  applySidebarWidth(sidebarOpenWidth);
});

form.addEventListener("submit", event => {
  event.preventDefault();

  if (waiting) {
    return;
  }

  const text = input.value.trim();
  const attachments = [...selectedChatFiles];

  if (!text && attachments.length === 0) {
    return;
  }

  if (!bridge) {
    addMessage("Qwen bağlantısı henüz hazır değil.", "assistant");
    return;
  }

  addMessage(attachmentDisplayText(text), "user");

  input.value = "";
  selectedChatFiles = [];
  renderAttachmentStrip();
  resize();
  setWaiting(true);
  startTimer();

  if (attachments.length > 0 && typeof bridge.send_message_with_attachments === "function") {
    bridge.send_message_with_attachments(text, JSON.stringify(attachments));
  } else {
    bridge.send_message(text);
  }
});

input.addEventListener("input", resize);

input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

applySidebarWidth(sidebarOpenWidth);
resize();
connectBridge();
