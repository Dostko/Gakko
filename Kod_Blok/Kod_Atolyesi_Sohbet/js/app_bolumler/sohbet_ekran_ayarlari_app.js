// SOHBET EKRAN AYARLARI: BAŞLANGIÇ

const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const stage = document.getElementById("chatStage");
const sendButton = document.getElementById("sendButton");
const sendButtonIdleHtml = sendButton.innerHTML;
const sendButtonIdleTitle = sendButton.title;
const sendButtonIdleAriaLabel = sendButton.getAttribute("aria-label");
const statusNote = document.getElementById("statusNote");

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

let waiting = false;
let cancelling = false;
let thinkingMessage = null;
let thinkingActivityList = null;
let thinkingActivityKeys = new Set();

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

function resize() {
  input.style.height = "40px";
  input.style.height = Math.max(40, Math.min(input.scrollHeight, 280)) + "px";
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
  title.style.fontWeight = "700";

  const activityList = document.createElement("div");
  activityList.style.display = "grid";
  activityList.style.gap = "3px";
  activityList.style.marginTop = "6px";
  activityList.style.fontSize = "12px";
  title.style.fontSize = "12px";
  activityList.style.color = "#6578bc";

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

  pendingAssistantImageAttachments = shouldOpenAttachedImageInAssistant(text, attachments)
    ? attachments.filter(isImageAttachment)
    : [];

  showThinkingMessage();

  input.value = "";
  selectedChatFiles = [];
  renderAttachmentStrip();
  resize();
  setWaiting(true);

  if (
    attachments.length > 0
    && typeof bridge.send_message_with_attachments === "function"
  ) {
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

resize();

// SOHBET EKRAN AYARLARI: BİTİŞ
