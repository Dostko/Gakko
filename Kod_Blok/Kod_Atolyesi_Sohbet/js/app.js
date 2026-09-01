const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const stage = document.getElementById("chatStage");
const sendButton = document.getElementById("sendButton");
const statusNote = document.getElementById("statusNote");
const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.getElementById("sidebarToggle");
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
const projectDirectoryCache = new Map();
const expandedProjectDirectories = new Set();

const SIDEBAR_MIN_WIDTH = 150;
const SIDEBAR_MAX_WIDTH = 520;

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

function addMessage(text, role) {
  const el = document.createElement("div");
  el.className = "message " + role;
  el.textContent = String(text || "");

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
  input.disabled = waiting;

  statusNote.textContent = waiting
    ? "Gakko düşünüyor..."
    : "Gakko • Qwen Code";

  if (!waiting) {
    input.focus();
  }
}

function connectBridge() {
  if (typeof QWebChannel === "undefined" || !window.qt || !qt.webChannelTransport) {
    statusNote.textContent = "Qwen bağlantısı kurulamadı";
    return;
  }

  new QWebChannel(qt.webChannelTransport, channel => {
    bridge = channel.objects.gakkoBridge;

    bridge.project_selected.connect(path => {
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
      setWaiting(true);
      startTimer();

      appShell.classList.add("sidebar-open");
      sidebarToggle.setAttribute("aria-expanded", "true");
      sidebarToggle.title = "Menüyü kapat";
    });

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

  if (!text) {
    return;
  }

  if (!bridge) {
    addMessage("Qwen bağlantısı henüz hazır değil.", "assistant");
    return;
  }

  addMessage(text, "user");

  input.value = "";
  resize();
  setWaiting(true);
  startTimer();

  bridge.send_message(text);
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
