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

// AI EKRAN ARACLARI: BITIS
