// DOSYA MENÜSÜ: BAŞLANGIÇ

const fileView = document.getElementById("fileView");
const fileOpenProjectButton = document.getElementById("fileOpenProjectButton");
const fileRemoveProjectButton = document.getElementById("fileRemoveProjectButton");
const fileActiveProjectName = document.getElementById("fileActiveProjectName");
const fileTreeList = document.getElementById("fileTreeList");
const fileReaderPane = document.getElementById("fileReaderPane");
const fileContent = document.getElementById("fileContent");
const fileViewResizer = document.getElementById("fileViewResizer");

let fileBrowserPath = "";
const fileDirectoryCache = new Map();
const expandedFileDirectories = new Set();

function requestFileDirectory(relativePath = "") {
  if (!bridge || typeof bridge.list_file_browser_directory !== "function") {
    return;
  }

  bridge.list_file_browser_directory(String(relativePath || ""));
}

function refreshVisibleFileDirectories() {
  if (!fileBrowserPath) {
    return;
  }

  requestFileDirectory("");
  expandedFileDirectories.forEach(path => requestFileDirectory(path));
}

function createFileTreeRow(entry, depth) {
  const row = document.createElement("button");
  row.type = "button";
  row.className = `file-tree-item ${entry.type}`;
  row.style.paddingLeft = `${8 + depth * 14}px`;
  row.title = entry.path;

  const marker = document.createElement("span");
  marker.className = "file-tree-marker";

  if (entry.type === "directory") {
    const opened = expandedFileDirectories.has(entry.path);
    marker.textContent = opened ? "⌄" : "›";
  } else {
    marker.textContent = "·";
  }

  const label = document.createElement("span");
  label.className = "file-tree-name";
  label.textContent = entry.name;

  row.appendChild(marker);
  row.appendChild(label);

  if (entry.type === "directory") {
    row.addEventListener("click", () => {
      if (expandedFileDirectories.has(entry.path)) {
        expandedFileDirectories.delete(entry.path);
        renderFileTree();
        return;
      }

      expandedFileDirectories.add(entry.path);
      if (!fileDirectoryCache.has(entry.path)) {
        requestFileDirectory(entry.path);
      }
      renderFileTree();
    });
  } else {
    row.addEventListener("click", () => {
      if (!bridge || typeof bridge.read_file_browser_file !== "function") {
        statusNote.textContent = "Dosya okuma bağlantısı henüz hazır değil";
        return;
      }

      statusNote.textContent = "Dosya okunuyor...";
      bridge.read_file_browser_file(entry.path);
    });
  }

  return row;
}

function appendFileTreeBranch(container, relativePath, depth) {
  const payload = fileDirectoryCache.get(relativePath);
  if (!payload) {
    return;
  }

  payload.entries.forEach(entry => {
    container.appendChild(createFileTreeRow(entry, depth));

    if (
      entry.type === "directory"
      && expandedFileDirectories.has(entry.path)
      && fileDirectoryCache.has(entry.path)
    ) {
      appendFileTreeBranch(container, entry.path, depth + 1);
    }
  });
}

function showFileTreeMessage(message) {
  fileTreeList.replaceChildren();
  const empty = document.createElement("div");
  empty.className = "file-tree-empty";
  empty.textContent = message;
  fileTreeList.appendChild(empty);
}

function renderFileTree() {
  const rootPayload = fileDirectoryCache.get("");

  if (!fileBrowserPath) {
    showFileTreeMessage("Proje Aç ile bir klasör seç.");
    return;
  }

  if (!rootPayload) {
    showFileTreeMessage("Proje dosyaları yükleniyor...");
    return;
  }

  fileTreeList.replaceChildren();

  if (rootPayload.entries.length === 0) {
    showFileTreeMessage("Henüz dosya yok");
    return;
  }

  appendFileTreeBranch(fileTreeList, "", 0);
}

function showFileReaderEmpty(message = "Okumak için soldan bir dosya seç.") {
  if (!fileReaderPane) {
    return;
  }

  const header = document.createElement("div");
  header.className = "file-pane-header";
  header.textContent = "DOSYA OKUMA";

  const empty = document.createElement("div");
  empty.className = "file-pane-empty";
  empty.textContent = message;

  fileReaderPane.replaceChildren(header, empty);
}

function renderFileBrowserFile(payload) {
  if (!fileReaderPane || !payload) {
    return;
  }

  const header = document.createElement("div");
  header.className = "file-pane-header";
  header.textContent = payload.name
    ? `DOSYA OKUMA · ${payload.name}`
    : "DOSYA OKUMA";

  if (payload.kind === "image" && payload.data_url) {
    const wrapper = document.createElement("div");
    wrapper.style.padding = "18px";
    wrapper.style.display = "flex";
    wrapper.style.justifyContent = "center";
    wrapper.style.alignItems = "flex-start";

    const image = document.createElement("img");
    image.src = String(payload.data_url);
    image.alt = String(payload.name || "Görsel");
    image.style.maxWidth = "100%";
    image.style.height = "auto";
    image.style.objectFit = "contain";

    wrapper.appendChild(image);
    fileReaderPane.replaceChildren(header, wrapper);
    statusNote.textContent = "Dosya açıldı";
    return;
  }

  const text = document.createElement("pre");
  text.textContent = String(payload.content || "");
  text.style.margin = "0";
  text.style.padding = "18px";
  text.style.boxSizing = "border-box";
  text.style.minHeight = "100%";
  text.style.whiteSpace = "pre-wrap";
  text.style.overflowWrap = "anywhere";
  text.style.fontFamily = "Consolas, 'Courier New', monospace";
  text.style.fontSize = "12px";
  text.style.lineHeight = "1.55";
  text.style.color = "#dfe7f0";

  fileReaderPane.replaceChildren(header, text);
  statusNote.textContent = "Dosya açıldı";
}

function showFileBrowserRoot(path) {
  const browserPath = String(path || "").trim();
  if (!browserPath) {
    return;
  }

  const cleanPath = browserPath.replace(/[\\/]+$/, "");
  const parts = cleanPath.split(/[\\/]/);
  const projectName = parts[parts.length - 1] || cleanPath;

  fileBrowserPath = browserPath;
  fileActiveProjectName.textContent = projectName;
  fileActiveProjectName.title = browserPath;
  fileRemoveProjectButton.hidden = false;

  fileDirectoryCache.clear();
  expandedFileDirectories.clear();
  renderFileTree();
  showFileReaderEmpty();
  requestFileDirectory("");
}

function resetFileTree() {
  fileDirectoryCache.clear();
  expandedFileDirectories.clear();
  renderFileTree();
}

function clearFileProjectView() {
  fileBrowserPath = "";
  fileActiveProjectName.textContent = "Yok";
  fileActiveProjectName.removeAttribute("title");
  fileRemoveProjectButton.hidden = true;
  resetFileTree();
  showFileReaderEmpty();
}

// DOSYA GÖRÜNÜMÜ PANEL BOYUTLANDIRMA: BAŞLANGIÇ

const FILE_TREE_MIN_WIDTH = 220;
const FILE_READER_MIN_WIDTH = 320;

let resizingFileView = false;
let fileResizePointerId = null;

function resizeFileTree(clientX) {
  if (!fileContent) {
    return;
  }

  const bounds = fileContent.getBoundingClientRect();

  if (bounds.width <= 0) {
    return;
  }

  const dividerSpace = 24;

  const maxWidth = Math.max(
    FILE_TREE_MIN_WIDTH,
    bounds.width - FILE_READER_MIN_WIDTH - dividerSpace
  );

  const requestedWidth = clientX - bounds.left;

  const width = Math.min(
    maxWidth,
    Math.max(FILE_TREE_MIN_WIDTH, requestedWidth)
  );

  fileContent.style.setProperty(
    "--file-tree-width",
    `${Math.round(width)}px`
  );
}

function stopFileResize() {
  if (!resizingFileView || !fileViewResizer) {
    return;
  }

  resizingFileView = false;
  fileViewResizer.classList.remove("dragging");

  document.body.style.cursor = "";
  document.body.style.userSelect = "";

  if (
    fileResizePointerId !== null
    && fileViewResizer.hasPointerCapture(fileResizePointerId)
  ) {
    fileViewResizer.releasePointerCapture(fileResizePointerId);
  }

  fileResizePointerId = null;
}

if (fileViewResizer && fileContent) {
  fileViewResizer.addEventListener("pointerdown", event => {
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();

    resizingFileView = true;
    fileResizePointerId = event.pointerId;

    fileViewResizer.setPointerCapture(event.pointerId);
    fileViewResizer.classList.add("dragging");

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    resizeFileTree(event.clientX);
  });

  fileViewResizer.addEventListener("pointermove", event => {
    if (!resizingFileView) {
      return;
    }

    resizeFileTree(event.clientX);
  });

  fileViewResizer.addEventListener("pointerup", stopFileResize);
  fileViewResizer.addEventListener("pointercancel", stopFileResize);
}

// DOSYA GÖRÜNÜMÜ PANEL BOYUTLANDIRMA: BİTİŞ

if (fileOpenProjectButton) {
  fileOpenProjectButton.addEventListener("click", () => {
    if (!bridge || typeof bridge.select_file_browser_folder !== "function") {
      statusNote.textContent = "Dosya klasörü seçici henüz hazır değil";
      return;
    }

    bridge.select_file_browser_folder();
  });
}

if (fileRemoveProjectButton) {
  fileRemoveProjectButton.addEventListener("click", () => {
    clearFileProjectView();
    statusNote.textContent = "Proje sayfadan kaldırıldı";
  });
}

// DOSYA MENÜSÜ: BİTİŞ
