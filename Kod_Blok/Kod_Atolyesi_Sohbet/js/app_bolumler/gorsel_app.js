// GÖRSEL / EKLER / KOD: BAŞLANGIÇ

const attachButton = document.getElementById("attachButton");

const attachmentStrip = document.createElement("div");
attachmentStrip.hidden = true;
attachmentStrip.style.display = "flex";
attachmentStrip.style.flexWrap = "wrap";
attachmentStrip.style.gap = "7px";
attachmentStrip.style.marginBottom = "8px";
attachmentStrip.style.padding = "0 4px";
form.insertAdjacentElement("beforebegin", attachmentStrip);

let selectedChatFiles = [];
let pendingAssistantImageAttachments = [];

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
  const dataUrl = String(file?.data_url || "").trim();
  if (/^data:image\//i.test(dataUrl)) {
    return dataUrl;
  }

  const fileUrl = attachmentPreviewUrl(file?.path);
  if (fileUrl) {
    return fileUrl;
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

function isSvgCodeBlock(codeText, language) {
  const normalizedLanguage = String(language || "").trim().toLowerCase();
  const normalizedCode = String(codeText || "").trim();

  if (!/^<svg[\s>]/i.test(normalizedCode)) {
    return false;
  }

  return normalizedLanguage === "" || normalizedLanguage === "svg" || normalizedLanguage === "xml";
}

function createSvgPreview(svgText) {
  const image = document.createElement("img");
  image.className = "assistant-image";
  image.alt = "GAKKO SVG görseli";
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(String(svgText || "").trim())}`;
  enableImagePreview(image);
  image.addEventListener("error", () => image.remove());
  return image;
}

function createCodeBlock(codeText, language) {
  if (isSvgCodeBlock(codeText, language)) {
    return createSvgPreview(codeText);
  }

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

function shouldOpenAttachedImageInAssistant(text, attachments = []) {
  const request = String(text || "").toLocaleLowerCase("tr-TR");
  const requestsOpen = /(?:aç|göster|görüntüle|sohbet penceresinde)/i.test(request);
  const hasImageAttachment = (Array.isArray(attachments) ? attachments : [])
    .some(isImageAttachment);
  return hasImageAttachment && requestsOpen;
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

// GÖRSEL / EKLER / KOD: BİTİŞ
