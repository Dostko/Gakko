// SOHBET / GÖRÜNÜM GEÇİŞLERİ: BAŞLANGIÇ

let selectedHistoryId = null;
let historySearchTimer = null;

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

  const existingIds = new Set(
    sessions.map(session => String(session.id || ""))
  );

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

// SOHBET / GÖRÜNÜM GEÇİŞLERİ: BİTİŞ
