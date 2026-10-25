// EKLER: BAŞLANGIÇ

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

// EKLER: BİTİŞ
