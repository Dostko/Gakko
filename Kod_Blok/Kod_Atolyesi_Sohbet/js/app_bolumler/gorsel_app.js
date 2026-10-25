// GÖRSEL: BAŞLANGIÇ

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
    const part = document.createElement("div");
    part.className = "message-text";
    appendAssistantMarkdown(part, parsed.visibleText);
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

// GÖRSEL: BİTİŞ
