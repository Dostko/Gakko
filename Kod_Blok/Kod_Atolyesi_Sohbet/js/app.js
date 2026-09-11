const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const stage = document.getElementById("chatStage");
const sendButton = document.getElementById("sendButton");
const sendButtonIdleHtml = sendButton.innerHTML;
const sendButtonIdleTitle = sendButton.title;
const sendButtonIdleAriaLabel = sendButton.getAttribute("aria-label");
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
const fileButton = document.getElementById("fileButton");

const fileView = document.getElementById("fileView");
const fileOpenProjectButton = document.getElementById("fileOpenProjectButton");
const fileRemoveProjectButton = document.getElementById("fileRemoveProjectButton");
const fileActiveProjectName = document.getElementById("fileActiveProjectName");
const fileTreeList = document.getElementById("fileTreeList");
const fileReaderPane = document.getElementById("fileReaderPane");
const fileContent = document.getElementById("fileContent");
const fileViewResizer = document.getElementById("fileViewResizer");

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
const activeProjectPathLabel = document.getElementById("activeProjectPath");
const sidebarResizer = document.getElementById("sidebarResizer");
const contextPanel = document.createElement("div");
contextPanel.style.display = "grid";
contextPanel.style.gridTemplateColumns = "1fr auto 1fr";
contextPanel.style.alignItems = "center";
contextPanel.style.gap = "12px";
contextPanel.style.marginTop = "8px";

const contextLeft = document.createElement("div");
contextLeft.style.display = "inline-flex";
contextLeft.style.alignItems = "center";
contextLeft.style.gap = "8px";
contextLeft.style.justifySelf = "start";

const remainingDisplay = document.createElement("span");
remainingDisplay.textContent = "Kalan —";
remainingDisplay.style.fontSize = "10px";
remainingDisplay.style.fontWeight = "600";
remainingDisplay.style.fontVariantNumeric = "tabular-nums";
remainingDisplay.style.letterSpacing = "0.3px";

const divider = document.createElement("span");
divider.textContent = "|";
divider.style.fontSize = "10px";
divider.style.color = "#566273";

const resetContextButton = document.createElement("button");
resetContextButton.type = "button";
resetContextButton.textContent = "Sıfırla";
resetContextButton.title = "Qwen Code bağlamını sıfırla";
resetContextButton.style.minHeight = "28px";
resetContextButton.style.padding = "0";
resetContextButton.style.border = "0";
resetContextButton.style.background = "transparent";
resetContextButton.style.color = "#8f9bad";
resetContextButton.style.fontSize = "10px";
resetContextButton.style.cursor = "pointer";

const shortcutNote = document.createElement("span");
shortcutNote.textContent = "Shift+Enter · Alt satır";
shortcutNote.style.fontSize = "10px";
shortcutNote.style.justifySelf = "end";

statusNote.insertAdjacentElement("afterend", contextPanel);
contextLeft.appendChild(remainingDisplay);
contextLeft.appendChild(divider);
contextLeft.appendChild(resetContextButton);
contextPanel.appendChild(contextLeft);
contextPanel.appendChild(statusNote);
contextPanel.appendChild(shortcutNote);
statusNote.style.justifySelf = "center";

let bridge = null;
let waiting = false;
let cancelling = false;
let sidebarOpenWidth = 240;
let resizingSidebar = false;
let currentView = "chat";
let selectedHistoryId = null;
let historySearchTimer = null;
let selectedChatFiles = [];
let pendingAssistantImageAttachments = [];
let thinkingMessage = null;
let thinkingActivityList = null;
let thinkingActivityKeys = new Set();
let activeProjectPath = "";
let fileBrowserPath = "";
const fileDirectoryCache = new Map();
const expandedFileDirectories = new Set();

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

function attachmentPreviewUrl(path) {
  const normalized = String(path || "").trim().replace(/\\/g, "/");
  if (!normalized) {
    return "";
  }
  return encodeURI(`file:///${normalized.replace(/^\/+/, "")}`);
}

function attachmentImageSrc(file) {
  const fileUrl = attachmentPreviewUrl(file?.path);
  if (fileUrl) {
    return fileUrl;
  }

  const dataUrl = String(file?.data_url || "").trim();
  if (/^data:image\//i.test(dataUrl)) {
    return dataUrl;
  }

  return "";
}

function isImageAttachment(file) {
  if (file && file.type === "image") {
    return true;
  }
  return /\.(png|jpe?g|webp|gif|bmp|svg|ico|tiff?)$/i.test(String(file?.path || ""));
}

function renderAttachmentStrip() {
  attachmentStrip.replaceChildren();
  attachmentStrip.hidden = selectedChatFiles.length === 0;

  let previewShown = false;

  selectedChatFiles.forEach(file => {
    const imageAttachment = isImageAttachment(file);
    const chip = document.createElement("div");
    chip.style.display = "inline-flex";
    chip.style.alignItems = "center";
    chip.style.gap = "7px";
    chip.style.maxWidth = "320px";
    chip.style.minHeight = "30px";
    chip.style.padding = "0 8px 0 10px";
    chip.style.border = "1px solid #253142";
    chip.style.borderRadius = "9px";
    chip.style.background = "#0d121b";
    chip.style.color = "#dfe7f0";
    chip.style.fontSize = "12px";
    chip.title = String(file.path || "");

    const icon = document.createElement("span");
    icon.textContent = imageAttachment ? "▧" : "▤";
    icon.style.color = imageAttachment ? "#6fb7ff" : "#aeb6c4";

    if (imageAttachment && !previewShown) {
      previewShown = true;
      const preview = document.createElement("img");
      preview.src = attachmentImageSrc(file);
      preview.alt = "";
      enableImagePreview(preview);
      preview.style.width = "84px";
      preview.style.height = "84px";
      preview.style.objectFit = "cover";
      preview.style.flex = "0 0 auto";
      preview.style.borderRadius = "6px";
      preview.style.border = "1px solid #28374c";
      chip.style.minHeight = "52px";
      chip.style.padding = "4px 8px 4px 4px";
      icon.hidden = true;
      preview.addEventListener("error", () => {
        preview.remove();
        icon.hidden = false;
      });
      chip.appendChild(preview);
    }

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
      type: file.type === "image" ? "image" : "file",
      data_url: String(file.data_url || "")
    });
  });

  selectedChatFiles = Array.from(byPath.values());
  renderAttachmentStrip();
}

window.addDroppedChatImages = files => {
  mergeSelectedChatFiles(Array.isArray(files) ? files : []);
  statusNote.textContent = "Görsel eklendi";
  input.focus();
};

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

function formatRemainingPercentage(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "Kalan —";
  }

  const clamped = Math.max(0, Math.min(100, number));
  return `Kalan %${clamped.toLocaleString("tr-TR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  })}`;
}

function resize() {
  input.style.height = "40px";
  input.style.height = Math.max(40, Math.min(input.scrollHeight, 280)) + "px";
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

function assistantImageUrl(reference) {
  let path = String(reference || "").trim();
  if (!path) {
    return "";
  }

  path = path
    .replace(/\\([()[\]_*&])/g, "$1")
    .replace(/^<|>$/g, "")
    .replace(/^[\'"]|[\'"]$/g, "")
    .trim();

  if (/^https?:\/\//i.test(path)) {
    try {
      const url = new URL(path);
      return url.username || url.password ? "" : url.toString();
    } catch (error) {
      return "";
    }
  }

  if (/^file:\/\/\//i.test(path)) {
    return encodeURI(path.replace(/\\/g, "/"));
  }

  if (/^[A-Za-z]:[\\/]/.test(path)) {
    return attachmentPreviewUrl(path);
  }

  if (!activeProjectPath || /^[a-z][a-z0-9+.-]*:/i.test(path)) {
    return "";
  }

  const base = String(activeProjectPath).replace(/[\\/]+$/, "");
  const relative = path.replace(/^[.][\\/]/, "");
  return attachmentPreviewUrl(`${base}/${relative}`);
}

function parseAssistantImages(text) {
  const source = String(text || "");
  const parseSource = source.replace(/\\([()[\]_*&])/g, "$1");
  const images = [];
  const seen = new Set();

  const add = reference => {
    const path = String(reference || "").trim();
    const normalized = assistantImageUrl(path) || path;
    const key = normalized.replace(/\\/g, "/").toLowerCase();
    if (path && !seen.has(key)) {
      seen.add(key);
      images.push(path);
    }
  };

  const markdownPattern = /!\[[^\]]*\]\(\s*<?(https?:\/\/[^\s<>\[\]]+|[^\r\n>\[]+?\.(?:png|jpe?g|webp|gif|bmp|svg|ico|tiff?)(?:\?[^\r\n>)]*)?)>?\s*\)/gi;
  let visibleText = parseSource.replace(markdownPattern, (full, reference) => {
    add(reference);
    return "";
  });

  const absolutePattern = /\b(?:file:\/\/\/)?[A-Za-z]:[\\/][^\r\n<>"|?*`]*?\.(?:png|jpe?g|webp|gif|bmp|svg|ico|tiff?)/gi;
  for (const match of parseSource.matchAll(absolutePattern)) {
    add(match[0]);
  }

  const remotePattern = /https?:\/\/[^\s<>"'\[\]]+/gi;
  for (const match of visibleText.matchAll(remotePattern)) {
    let reference = match[0];
    let extraClosing = (reference.match(/\)/g) || []).length
      - (reference.match(/\(/g) || []).length;
    while (extraClosing > 0 && reference.endsWith(")")) {
      reference = reference.slice(0, -1);
      extraClosing -= 1;
    }
    if (/\.(?:png|jpe?g|webp|gif|bmp|svg|ico|tiff?)(?:[?#]|$)/i.test(reference)) {
      add(reference);
    }
  }

  parseSource.split(/\r?\n/).forEach(line => {
    const path = line.trim().replace(/^`+|`+$/g, "").trim();
    if (
      /^(?:\.{0,2}[\\/])?[\w .()@+\-\\/]+\.(?:png|jpe?g|webp|gif|bmp|svg|ico|tiff?)$/i.test(path)
      && /[\\/]/.test(path)
    ) {
      add(path);
    }
  });

  return { visibleText, images };
}

function appendPlainAssistantText(container, text, renderedImageKeys) {
  if (!text) {
    return;
  }

  const parsed = parseAssistantImages(text);

  parsed.images.forEach(path => {
    const key = String(path || "").trim().replace(/\\/g, "/").toLowerCase();
    if (!key || renderedImageKeys.has(key)) {
      return;
    }

    const src = assistantImageUrl(path);
    if (!src) {
      return;
    }

    renderedImageKeys.add(key);

    const image = document.createElement("img");
    image.className = "assistant-image";
    image.referrerPolicy = "no-referrer";
    image.src = src;
    image.alt = "GAKKO görseli";
    enableImagePreview(image);
    image.addEventListener("error", () => image.remove());
    container.appendChild(image);
  });

  if (parsed.visibleText) {
    const part = document.createElement("span");
    part.className = "message-text";
    part.textContent = parsed.visibleText;
    container.appendChild(part);
  }
}

function shouldOpenAttachedImageInAssistant(text) {
  const request = String(text || "").toLocaleLowerCase("tr-TR");
  const mentionsImage = /(?:görsel|resim|foto(?:ğraf)?|ekran görüntüsü)/i.test(request);
  const requestsOpen = /(?:aç|göster|görüntüle|sohbet penceresinde)/i.test(request);
  return mentionsImage && requestsOpen;
}

function renderAssistantAttachmentImages(container, attachments = []) {
  const files = Array.isArray(attachments) ? attachments : [];
  const rendered = new Set();

  files.forEach(file => {
    if (!isImageAttachment(file)) {
      return;
    }

    const src = attachmentImageSrc(file);
    if (!src || rendered.has(src)) {
      return;
    }

    rendered.add(src);

    const image = document.createElement("img");
    image.className = "assistant-image";
    image.src = src;
    image.alt = String(file.name || "GAKKO görseli");
    enableImagePreview(image);
    image.addEventListener("error", () => image.remove());
    container.appendChild(image);
  });
}

function renderAssistantContent(container, text, attachments = []) {
  renderAssistantAttachmentImages(container, attachments);

  const source = String(text || "");
  const fencePattern = /```([^\n`]*)\n([\s\S]*?)```/g;
  const renderedImageKeys = new Set();
  let cursor = 0;
  let match = null;

  while ((match = fencePattern.exec(source)) !== null) {
    appendPlainAssistantText(container, source.slice(cursor, match.index), renderedImageKeys);
    container.appendChild(createCodeBlock(match[2].replace(/\n$/, ""), match[1]));
    cursor = match.index + match[0].length;
  }

  appendPlainAssistantText(container, source.slice(cursor), renderedImageKeys);
}

function renderUserMessage(container, text, attachments = []) {
  const cleanText = String(text || "").trim();

  if (cleanText) {
    const messageText = document.createElement("div");
    messageText.textContent = cleanText;
    container.appendChild(messageText);
  }

  const files = Array.isArray(attachments) ? attachments : [];
  if (files.length === 0) {
    return;
  }

  const attachmentList = document.createElement("div");
  attachmentList.style.display = "flex";
  attachmentList.style.flexDirection = "column";
  attachmentList.style.gap = "6px";
  attachmentList.style.marginTop = cleanText ? "8px" : "0";

  files.forEach(file => {
    const row = document.createElement("div");
    row.style.display = "inline-flex";
    row.style.alignItems = "center";
    row.style.gap = "7px";
    row.style.maxWidth = "320px";

    if (isImageAttachment(file)) {
      const preview = document.createElement("img");
      preview.src = attachmentImageSrc(file);
      preview.alt = "";
      enableImagePreview(preview);
      preview.style.width = "84px";
      preview.style.height = "84px";
      preview.style.objectFit = "cover";
      preview.style.flex = "0 0 auto";
      preview.style.borderRadius = "6px";
      preview.style.border = "1px solid #253142";
      preview.addEventListener("error", () => preview.remove());
      row.appendChild(preview);
    }

    const label = document.createElement("span");
    label.textContent = `Ekler: ${String(file.name || "dosya")}`;
    label.style.overflow = "hidden";
    label.style.textOverflow = "ellipsis";
    label.style.whiteSpace = "nowrap";
    row.appendChild(label);

    attachmentList.appendChild(row);
  });

  container.appendChild(attachmentList);
}

function addMessage(text, role, attachments = []) {
  const el = document.createElement("div");
  el.className = "message " + role;

  if (role === "assistant") {
    renderAssistantContent(el, text, attachments);
  } else {
    renderUserMessage(el, text, attachments);
  }

  messages.appendChild(el);
  welcome.classList.add("hidden");

  stage.scrollTo({
    top: stage.scrollHeight,
    behavior: "smooth"
  });
}

function showThinkingMessage() {
  removeThinkingMessage();

  const el = document.createElement("div");
  el.className = "message assistant";
  el.dataset.transient = "thinking";

  const title = document.createElement("div");
  title.textContent = "GAKKO düşünüyor...";
  title.style.fontWeight = "600";

  const activityList = document.createElement("div");
  activityList.style.display = "grid";
  activityList.style.gap = "3px";
  activityList.style.marginTop = "6px";
  activityList.style.fontSize = "12px";
  activityList.style.color = "#8f9bad";

  el.appendChild(title);
  el.appendChild(activityList);
  messages.appendChild(el);
  welcome.classList.add("hidden");

  thinkingMessage = el;
  thinkingActivityList = activityList;
  thinkingActivityKeys = new Set();

  stage.scrollTo({
    top: stage.scrollHeight,
    behavior: "smooth"
  });
}

function removeThinkingMessage() {
  if (thinkingMessage) {
    thinkingMessage.remove();
  }

  thinkingMessage = null;
  thinkingActivityList = null;
  thinkingActivityKeys = new Set();
}

function activityDetail(payload) {
  const rawPath = String(payload.path || "").trim().replace(/\\/g, "/");
  const fileName = rawPath ? rawPath.split("/").pop() : "";
  const query = String(payload.query || payload.pattern || "").trim();

  return {
    fileName,
    query: query.length > 70 ? `${query.slice(0, 67)}...` : query
  };
}

function formatThinkingActivity(payload) {
  const name = String(payload.name || "").trim();
  const detail = activityDetail(payload);

  if (name === "search") {
    return detail.query
      ? `Dosyalarda aranıyor · ${detail.query}`
      : "Dosyalarda aranıyor";
  }

  if (name === "read_text_file" || name === "read_media_file") {
    return detail.fileName
      ? `Dosya okunuyor · ${detail.fileName}`
      : "Dosya okunuyor";
  }

  if (name === "read_multiple_files") {
    return "Dosyalar okunuyor";
  }

  if (["list_directory", "list_directory_with_sizes", "directory_tree"].includes(name)) {
    return "Klasör inceleniyor";
  }

  if (name === "get_file_info") {
    return detail.fileName
      ? `Dosya bilgisi kontrol ediliyor · ${detail.fileName}`
      : "Dosya bilgisi kontrol ediliyor";
  }

  if (name === "edit_file" || name === "write_file") {
    return detail.fileName
      ? `Dosya düzenleniyor · ${detail.fileName}`
      : "Dosya düzenleniyor";
  }

  if (name === "create_directory") {
    return "Klasör oluşturuluyor";
  }

  if (name === "move_file") {
    return "Dosya taşınıyor";
  }

  if (name === "web_search") {
    return "İnternette araştırılıyor";
  }

  if (name === "web_fetch") {
    return "Web sayfası okunuyor";
  }

  if (payload.url) {
    return "İnternette işlem yapılıyor";
  }

  return name ? `Araç kullanılıyor · ${name}` : "";
}

function appendThinkingActivity(payloadText) {
  if (!thinkingMessage || !thinkingActivityList) {
    return;
  }

  let payload = null;
  try {
    payload = JSON.parse(String(payloadText || "{}"));
  } catch (error) {
    return;
  }

  const text = formatThinkingActivity(payload);
  if (!text || thinkingActivityKeys.has(text)) {
    return;
  }

  thinkingActivityKeys.add(text);

  const line = document.createElement("div");
  line.textContent = `↳ ${text}`;
  thinkingActivityList.appendChild(line);

  stage.scrollTo({
    top: stage.scrollHeight,
    behavior: "smooth"
  });
}

function setWaiting(value) {
  waiting = Boolean(value);
  if (!waiting) {
    cancelling = false;
  }

  sendButton.disabled = cancelling;
  if (waiting) {
    sendButton.textContent = "■";
    sendButton.title = "Qwen yanıtını durdur";
    sendButton.setAttribute("aria-label", "Qwen yanıtını durdur");
  } else {
    sendButton.innerHTML = sendButtonIdleHtml;
    sendButton.title = sendButtonIdleTitle;
    if (sendButtonIdleAriaLabel === null) {
      sendButton.removeAttribute("aria-label");
    } else {
      sendButton.setAttribute("aria-label", sendButtonIdleAriaLabel);
    }
  }
  attachButton.disabled = waiting;
  resetContextButton.disabled = waiting;
  resetContextButton.style.opacity = waiting ? "0.45" : "1";
  input.disabled = waiting;

  statusNote.textContent = "Gakko AI";

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
  const projectName = parts[parts.length - 1] || cleanPath;

  activeProjectPath = projectPath;

  activeProjectName.textContent = projectName;
  activeProjectPathLabel.textContent = projectPath;
  activeProject.hidden = false;

  if (startsProjectMethod) {
    projectMenu.hidden = false;
    projectButton.setAttribute("aria-expanded", "true");
    syncSidebarActiveState(true);
    setWaiting(true);
  } else {
    projectMenu.hidden = true;
    projectButton.setAttribute("aria-expanded", "false");
    syncSidebarActiveState(false);
  }
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

function syncSidebarActiveState(projectOpen = false) {
  const historyOpen = currentView === "history";
  const filesOpen = currentView === "files";
  const chatOpen = currentView === "chat";

  projectButton.classList.toggle("active", projectOpen);
  historyButton.classList.toggle("active", !projectOpen && historyOpen);

  if (fileButton) {
    fileButton.classList.toggle("active", !projectOpen && filesOpen);
  }

  chatButton.classList.toggle("active", !projectOpen && chatOpen);
}

function setMainView(view) {
  if (view === "history") {
    currentView = "history";
  } else if (view === "files" && fileView) {
    currentView = "files";
  } else {
    currentView = "chat";
  }

  const historyOpen = currentView === "history";
  const filesOpen = currentView === "files";
  const chatOpen = currentView === "chat";

  historyView.hidden = !historyOpen;

  if (fileView) {
    fileView.hidden = !filesOpen;
  }

  stage.hidden = !chatOpen;
  composerArea.hidden = !chatOpen;

  if (!projectMenu.hidden) {
    projectMenu.hidden = true;
    projectButton.setAttribute("aria-expanded", "false");
  }

  syncSidebarActiveState(false);

  if (chatOpen) {
    input.focus();
  }
}

/* =========================================
   DOSYA GÖRÜNÜMÜ PANEL BOYUTLANDIRMA
   ========================================= */

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

    if (
      bridge.file_browser_project_selected
      && typeof bridge.file_browser_project_selected.connect === "function"
    ) {
      bridge.file_browser_project_selected.connect(path => {
        showFileBrowserRoot(path);
      });
    }

    if (
      bridge.file_browser_directory_ready
      && typeof bridge.file_browser_directory_ready.connect === "function"
    ) {
      bridge.file_browser_directory_ready.connect(payloadText => {
        try {
          const payload = JSON.parse(String(payloadText || "{}"));
          const path = String(payload.path || "");
          const entries = Array.isArray(payload.entries) ? payload.entries : [];
          fileDirectoryCache.set(path, { path, entries });
          renderFileTree();
        } catch (error) {
          statusNote.textContent = "Dosya klasörü okunamadı";
        }
      });
    }

    if (
      bridge.file_browser_file_ready
      && typeof bridge.file_browser_file_ready.connect === "function"
    ) {
      bridge.file_browser_file_ready.connect(payloadText => {
        try {
          renderFileBrowserFile(JSON.parse(String(payloadText || "{}")));
        } catch (error) {
          statusNote.textContent = "Dosya açılamadı";
        }
      });
    }

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

    if (
      bridge.context_remaining_ready
      && typeof bridge.context_remaining_ready.connect === "function"
    ) {
      bridge.context_remaining_ready.connect(value => {
        remainingDisplay.textContent = formatRemainingPercentage(value);
        if (!waiting && statusNote.textContent === "Bağlam sıfırlanıyor...") {
          statusNote.textContent = "Gakko AI";
        }
      });
    }

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
      removeThinkingMessage();
      const assistantImages = pendingAssistantImageAttachments;
      pendingAssistantImageAttachments = [];
      addMessage(reply, "assistant", assistantImages);
      setWaiting(false);
      refreshVisibleFileDirectories();
    });

    if (
      bridge.tool_activity
      && typeof bridge.tool_activity.connect === "function"
    ) {
      bridge.tool_activity.connect(payloadText => {
        appendThinkingActivity(payloadText);
      });
    }

    if (
      bridge.generation_cancelled
      && typeof bridge.generation_cancelled.connect === "function"
    ) {
      bridge.generation_cancelled.connect(() => {
        pendingAssistantImageAttachments = [];
        removeThinkingMessage();
        addMessage("İşlem durduruldu.", "assistant");
        setWaiting(false);
        statusNote.textContent = "İşlem durduruldu";
      });
    }

    bridge.error_ready.connect(error => {
      pendingAssistantImageAttachments = [];
      removeThinkingMessage();
      addMessage("Hata: " + error, "assistant");
      setWaiting(false);
    });

    statusNote.textContent = "Gakko AI";
  });
}

function closeProjectMenu() {
  projectMenu.hidden = true;
  projectButton.setAttribute("aria-expanded", "false");
  syncSidebarActiveState(false);
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

resetContextButton.addEventListener("click", () => {
  if (waiting) {
    return;
  }

  if (!bridge || typeof bridge.reset_qwen_context !== "function") {
    statusNote.textContent = "Sıfırlama bağlantısı henüz hazır değil";
    return;
  }

  remainingDisplay.textContent = "Kalan …";
  statusNote.textContent = "Bağlam sıfırlanıyor...";
  bridge.reset_qwen_context();
});

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

if (fileButton) {
  fileButton.addEventListener("click", () => {
    setMainView("files");
  });
}

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
  syncSidebarActiveState(opened);
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
    if (cancelling) {
      return;
    }
    if (!bridge || typeof bridge.cancel_generation !== "function") {
      statusNote.textContent = "Durdurma bağlantısı hazır değil";
      return;
    }

    cancelling = true;
    sendButton.disabled = true;
    statusNote.textContent = "Yanıt durduruluyor...";
    bridge.cancel_generation();
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

  addMessage(text, "user", attachments);
  pendingAssistantImageAttachments = shouldOpenAttachedImageInAssistant(text)
    ? attachments.filter(isImageAttachment)
    : [];
  showThinkingMessage();

  input.value = "";
  selectedChatFiles = [];
  renderAttachmentStrip();
  resize();
  setWaiting(true);

  if (attachments.length > 0 && typeof bridge.send_message_with_attachments === "function") {
    bridge.send_message_with_attachments(text, JSON.stringify(attachments));
  } else {
    bridge.send_message(text);
  }
});

input.addEventListener("input", resize);


input.addEventListener("paste", event => {
  const clipboard = event.clipboardData;
  if (!clipboard) {
    return;
  }

  const imageItem = Array.from(clipboard.items || []).find(
    item => item.kind === "file" && String(item.type || "").startsWith("image/")
  );

  if (!imageItem) {
    return;
  }

  if (waiting) {
    event.preventDefault();
    statusNote.textContent = "GAKKO yanıt verirken görsel eklenemez";
    return;
  }

  if (!bridge || typeof bridge.add_clipboard_image !== "function") {
    event.preventDefault();
    statusNote.textContent = "Pano görsel bağlantısı henüz hazır değil";
    return;
  }

  const file = imageItem.getAsFile();
  if (!file) {
    return;
  }

  event.preventDefault();

  if (file.size > 12 * 1024 * 1024) {
    statusNote.textContent = "Pano görseli 12 MB sınırını aşıyor";
    return;
  }

  const reader = new FileReader();

  reader.addEventListener("load", () => {
    const dataUrl = String(reader.result || "");
    if (!dataUrl) {
      statusNote.textContent = "Pano görseli okunamadı";
      return;
    }

    statusNote.textContent = "Görsel ekleniyor...";
    bridge.add_clipboard_image(dataUrl);
  });

  reader.addEventListener("error", () => {
    statusNote.textContent = "Pano görseli okunamadı";
  });

  reader.readAsDataURL(file);
});

input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

applySidebarWidth(sidebarOpenWidth);
resize();
connectBridge();

// GÖRSEL BÜYÜK ÖNİZLEME: BAŞLANGIÇ
function enableImagePreview(image) {
  image.classList.add("image-preview-trigger");
  image.tabIndex = 0;
  image.setAttribute("role", "button");
  image.setAttribute("aria-label", "Görseli büyüt");
  image.addEventListener("click", () => openImagePreview(image));
  image.addEventListener("keydown", event => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openImagePreview(image);
    }
  });
}

function openImagePreview(source) {
  const src = source.currentSrc || source.src;
  if (!src) return;

  const dialog = document.createElement("dialog");
  dialog.className = "image-preview-dialog";
  dialog.setAttribute("aria-label", "Görsel büyük önizleme");

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "image-preview-close";
  closeButton.textContent = "×";
  closeButton.setAttribute("aria-label", "Önizlemeyi kapat");

  const image = document.createElement("img");
  image.className = "image-preview-full";
  image.referrerPolicy = source.referrerPolicy;
  image.alt = source.alt || "Görsel";
  image.src = src;

  closeButton.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    dialog.remove();
    if (source.isConnected) source.focus({ preventScroll: true });
  }, { once: true });

  dialog.append(closeButton, image);
  document.body.appendChild(dialog);
  dialog.showModal();
  closeButton.focus();
}
// GÖRSEL BÜYÜK ÖNİZLEME: BİTİŞ
