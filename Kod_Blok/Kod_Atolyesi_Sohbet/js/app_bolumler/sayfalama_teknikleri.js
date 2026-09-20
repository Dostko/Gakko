// SOHBET SAYFALAMA: BASLANGIC

function renderActiveChatPage(payload) {
  const chat = payload && typeof payload === "object" ? payload : {};
  const restoredMessages = Array.isArray(chat.messages) ? chat.messages : [];

  removeThinkingMessage();
  pendingAssistantImageAttachments = [];
  messages.replaceChildren();

  if (restoredMessages.length === 0) {
    welcome.classList.remove("hidden");
    remainingDisplay.textContent = formatRemainingPercentage(100);
    statusNote.textContent = "Gakko AI";
    input.focus();
    return;
  }

  restoredMessages.forEach(message => {
    const role = message.role === "user" ? "user" : "assistant";
    addMessage(String(message.content || ""), role);
  });

  window.requestAnimationFrame(() => {
    stage.scrollTo({
      top: stage.scrollHeight,
      behavior: "auto"
    });
  });

  statusNote.textContent = "Gakko AI";
  input.focus();
}

function initializeChatPagination(chatBridge) {
  if (
    !chatBridge
    || !chatBridge.active_chat_ready
    || typeof chatBridge.active_chat_ready.connect !== "function"
  ) {
    statusNote.textContent = "Sohbet sayfası bağlantısı kurulamadı";
    return;
  }

  chatBridge.active_chat_ready.connect(payloadText => {
    try {
      renderActiveChatPage(JSON.parse(String(payloadText || "{}")));
    } catch (error) {
      statusNote.textContent = "Sohbet sayfası geri yüklenemedi";
    }
  });

  if (typeof chatBridge.load_active_chat === "function") {
    chatBridge.load_active_chat();
  }
}

// SOHBET SAYFALAMA: BITIS
