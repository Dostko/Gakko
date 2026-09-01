const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const stage = document.getElementById("chatStage");
const sendButton = document.getElementById("sendButton");
const statusNote = document.getElementById("statusNote");
const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.getElementById("sidebarToggle");
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

    bridge.reply_ready.connect(reply => {
      addMessage(reply, "assistant");
      setWaiting(false);
      stopTimer();
    });

    bridge.error_ready.connect(error => {
      addMessage("Hata: " + error, "assistant");
      setWaiting(false);
      stopTimer();
    });

    statusNote.textContent = "Gakko AI";
  });
}

sidebarToggle.addEventListener("click", () => {
  const opened = appShell.classList.toggle("sidebar-open");

  sidebarToggle.setAttribute("aria-expanded", String(opened));
  sidebarToggle.title = opened
    ? "Menüyü kapat"
    : "Menüyü aç";
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

resize();
connectBridge();
