// AI EKRAN ARACLARI: BASLANGIC

// MESAJ KOPYALAMA: BASLANGIC

function setMessageCopyState(button, copied) {
  button.classList.toggle("copied", copied);
  button.title = copied ? "Kopyalandı" : "Kopyalanamadı";
  button.setAttribute("aria-label", copied ? "Kopyalandı" : "Kopyalanamadı");

  window.setTimeout(() => {
    button.classList.remove("copied");
    button.title = "Mesajı kopyala";
    button.setAttribute("aria-label", "Mesajı kopyala");
  }, 1200);
}

function copyMessageText(text, button) {
  const value = String(text || "");

  if (!value || !bridge || typeof bridge.copy_text_to_clipboard !== "function") {
    setMessageCopyState(button, false);
    return;
  }

  try {
    bridge.copy_text_to_clipboard(value, copied => {
      setMessageCopyState(button, Boolean(copied));
    });
  } catch (error) {
    setMessageCopyState(button, false);
  }
}

function createMessageCopyButton(text) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-copy-button";
  button.title = "Mesajı kopyala";
  button.setAttribute("aria-label", "Mesajı kopyala");
  button.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="8" y="8" width="11" height="11" rx="2"></rect>
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"></path>
    </svg>
  `;

  button.addEventListener("click", event => {
    event.stopPropagation();
    copyMessageText(text, button);
  });

  return button;
}

// MESAJ KOPYALAMA: BITIS

// MESAJ AVATARLARI: BASLANGIC

const MESSAGE_AVATAR_PATHS = {
  assistant: "assets/ikonlar/gakko_avatar.svg",
  user: "assets/ikonlar/kullanici_avatar.svg"
};

function createMessageAvatar(role) {
  const image = document.createElement("img");
  image.className = `message-avatar message-avatar-${role}`;
  image.src = MESSAGE_AVATAR_PATHS[role];
  image.alt = "";
  image.setAttribute("aria-hidden", "true");
  image.draggable = false;
  return image;
}

function decorateMessageAvatar(message) {
  if (!(message instanceof HTMLElement)) return;
  if (!message.classList.contains("message")) return;
  if (message.dataset.transient === "thinking") return;
  if (message.querySelector(":scope > .message-avatar")) return;

  const role = message.classList.contains("assistant")
    ? "assistant"
    : message.classList.contains("user")
      ? "user"
      : "";

  if (!role) return;

  message.classList.add("has-message-avatar");
  message.prepend(createMessageAvatar(role));
}

function initializeMessageAvatars() {
  const container = document.getElementById("messages");
  if (!container) return;

  container.querySelectorAll(".message").forEach(decorateMessageAvatar);

  const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (!(node instanceof HTMLElement)) return;
        decorateMessageAvatar(node);
        node.querySelectorAll?.(".message").forEach(decorateMessageAvatar);
      });
    });
  });

  observer.observe(container, {
    childList: true,
    subtree: true
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeMessageAvatars, { once: true });
} else {
  initializeMessageAvatars();
}

// MESAJ AVATARLARI: BITIS


// ASAGI DON BUTONU: BASLANGIC

function createScrollToBottomButton() {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "chat-scroll-bottom-button";
  button.title = "Son mesaja dön";
  button.setAttribute("aria-label", "Son mesaja dön");
  button.hidden = true;
  button.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5v13"></path>
      <path d="m6.5 12.5 5.5 5.5 5.5-5.5"></path>
    </svg>
  `;
  return button;
}

function initializeScrollToBottomButton() {
  const stage = document.getElementById("chatStage");
  const composerArea = document.querySelector(".composer-area");
  const messagesContainer = document.getElementById("messages");

  if (!stage || !composerArea || !messagesContainer) return;
  if (composerArea.querySelector(".chat-scroll-bottom-button")) return;

  const button = createScrollToBottomButton();
  composerArea.appendChild(button);

  const updateVisibility = () => {
    const distanceFromBottom = stage.scrollHeight - stage.scrollTop - stage.clientHeight;
    button.hidden = distanceFromBottom < 120;
  };

  button.addEventListener("click", () => {
    stage.scrollTo({
      top: stage.scrollHeight,
      behavior: "smooth"
    });
  });

  stage.addEventListener("scroll", updateVisibility, { passive: true });

  const observer = new MutationObserver(updateVisibility);
  observer.observe(messagesContainer, {
    childList: true,
    subtree: true
  });

  window.addEventListener("resize", updateVisibility, { passive: true });
  updateVisibility();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeScrollToBottomButton, { once: true });
} else {
  initializeScrollToBottomButton();
}

// ASAGI DON BUTONU: BITIS

// AI EKRAN ARACLARI: BITIS
