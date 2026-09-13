// KAYITLAR PANELI: BASLANGIC

let selectedRecordName = null;
let recordsSearchTimer = null;

function formatRecordDate(value) {
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

function requestRecords(query = recordsSearch.value) {
  if (!recordsBridge || typeof recordsBridge.list_records !== "function") {
    statusNote.textContent = "Kayıtlar bağlantısı henüz hazır değil";
    return;
  }

  recordsBridge.list_records(String(query || ""));
}

function clearRecordDetail(message = "Okumak için soldan bir kayıt seç.") {
  selectedRecordName = null;
  recordsDetail.replaceChildren();

  const empty = document.createElement("div");
  empty.className = "records-empty";
  empty.textContent = message;
  recordsDetail.appendChild(empty);
}

function renderRecordsList(payload) {
  const records = Array.isArray(payload.records) ? payload.records : [];
  recordsList.replaceChildren();

  if (records.length === 0) {
    const empty = document.createElement("div");
    empty.className = "records-empty";
    empty.textContent = recordsSearch.value.trim()
      ? "Aramayla eşleşen kayıt bulunamadı."
      : "Henüz kalıcı kayıt yok.";
    recordsList.appendChild(empty);
    clearRecordDetail();
    return;
  }

  const names = new Set(records.map(record => String(record.name || "")));
  if (selectedRecordName && !names.has(selectedRecordName)) {
    clearRecordDetail();
  }

  records.forEach(record => {
    const name = String(record.name || "");
    const item = document.createElement("button");
    item.type = "button";
    item.className = "records-item";

    if (name === selectedRecordName) {
      item.classList.add("active");
    }

    const title = document.createElement("strong");
    title.textContent = String(record.title || name || "Kayıt");

    const meta = document.createElement("div");
    meta.className = "records-item-meta";
    const parts = [formatRecordDate(record.updated_at)];
    if (record.size_text) {
      parts.push(String(record.size_text));
    }
    meta.textContent = parts.filter(Boolean).join(" · ");

    item.appendChild(title);
    item.appendChild(meta);
    item.addEventListener("click", () => {
      selectedRecordName = name;
      renderRecordsList(payload);
      if (recordsBridge && typeof recordsBridge.get_record === "function") {
        recordsBridge.get_record(name);
      }
    });

    recordsList.appendChild(item);
  });
}

function renderRecordDetail(record) {
  if (!record || !record.name) {
    clearRecordDetail("Bu kayıt artık bulunamıyor.");
    return;
  }

  selectedRecordName = String(record.name);
  recordsDetail.replaceChildren();

  const head = document.createElement("div");
  head.className = "records-detail-head";

  const info = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = String(record.title || record.name || "Kayıt");

  const meta = document.createElement("div");
  meta.className = "records-detail-meta";
  const parts = [String(record.name || ""), formatRecordDate(record.updated_at)];
  if (record.size_text) {
    parts.push(String(record.size_text));
  }
  meta.textContent = parts.filter(Boolean).join(" · ");

  info.appendChild(title);
  info.appendChild(meta);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "records-delete-one";
  deleteButton.textContent = "Kaydı sil";
  deleteButton.addEventListener("click", () => {
    const name = String(record.name || "");
    if (!name || !confirm(`\"${name}\" kalıcı olarak silinsin mi?`)) {
      return;
    }

    if (recordsBridge && typeof recordsBridge.delete_record === "function") {
      recordsBridge.delete_record(name);
    }
  });

  head.appendChild(info);
  head.appendChild(deleteButton);
  recordsDetail.appendChild(head);

  const content = document.createElement("pre");
  content.className = "records-document";
  content.textContent = String(record.content || "");
  recordsDetail.appendChild(content);
}

if (recordsButton) {
  recordsButton.addEventListener("click", () => {
    setMainView("records");
    requestRecords();
  });
}

if (recordsSearch) {
  recordsSearch.addEventListener("input", () => {
    if (recordsSearchTimer !== null) {
      clearTimeout(recordsSearchTimer);
    }
    recordsSearchTimer = setTimeout(() => requestRecords(), 180);
  });
}

if (recordsRefreshButton) {
  recordsRefreshButton.addEventListener("click", () => {
    requestRecords();
  });
}

// KAYITLAR PANELI: BITIS
