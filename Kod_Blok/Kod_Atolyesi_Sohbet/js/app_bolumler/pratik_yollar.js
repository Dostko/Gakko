// PRATIK YOLLAR: BASLANGIC

(() => {
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");

  if (!chatForm || !messageInput || document.getElementById("pratikYollarPanel")) {
    return;
  }

  const commands = [
    {
      command: "/proje",
      title: "Proje",
      description: "Aktif projeyi incele ve mevcut durumu özetle",
      prompt: "Aktif projeyi incele ve mevcut durumu kısa şekilde özetle.",
      inlinePrompt: "aktif projeyi incele ve mevcut durumu kısa şekilde özetle."
    },
    {
      command: "/ocr",
      title: "OCR",
      description: "Ekli görseldeki metni oku",
      prompt: "Ekli görseldeki metni oku ve metin olarak çıkar.",
      inlinePrompt: "ekli görseldeki metni oku ve metin olarak çıkar."
    },
    {
      command: "/git",
      title: "Git",
      description: "Mevcut çalışma için güvenli checkpoint al",
      prompt: "Git kaydında pusula yönerglerine göre al.",
      inlinePrompt: "Git kaydını yönergelere göre al."
    },
    {
      command: "/ozet",
      title: "Özet",
      description: "Sohbet durumunu ve sıradaki işi özetle",
      prompt: "Bu sohbetin mevcut durumunu ve sıradaki işi kısa şekilde özetle.",
      inlinePrompt: "mevcut durumu ve sıradaki işi kısa şekilde özetle."
    }
  ];

  const style = document.createElement("style");
  style.id = "pratikYollarStyle";
  style.textContent = `
    .pratik-yollar-panel {
      display: grid;
      gap: 4px;
      margin: 0 0 8px;
      padding: 7px;
      border: 1px solid rgba(255, 255, 255, 0.09);
      border-radius: 12px;
      background: rgba(20, 24, 32, 0.98);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
    }

    .pratik-yollar-panel[hidden] {
      display: none;
    }

    .pratik-yol-item {
      display: grid;
      grid-template-columns: 76px 1fr;
      gap: 10px;
      align-items: center;
      width: 100%;
      padding: 8px 10px;
      border: 0;
      border-radius: 9px;
      background: transparent;
      color: inherit;
      text-align: left;
      cursor: pointer;
    }

    .pratik-yol-item:hover,
    .pratik-yol-item.is-selected {
      background: rgba(255, 255, 255, 0.07);
    }

    .pratik-yol-command {
      color: #ff8fb4;
      font-weight: 700;
      font-size: 12px;
    }

    .pratik-yol-detail {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    .pratik-yol-title {
      font-size: 12px;
      font-weight: 650;
      color: #edf1f7;
    }

    .pratik-yol-description {
      overflow: hidden;
      color: #8f9bad;
      font-size: 10px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `;
  document.head.appendChild(style);

  const panel = document.createElement("div");
  panel.id = "pratikYollarPanel";
  panel.className = "pratik-yollar-panel";
  panel.setAttribute("role", "listbox");
  panel.setAttribute("aria-label", "Pratik yollar");
  panel.hidden = true;
  chatForm.insertAdjacentElement("beforebegin", panel);

  let visibleCommands = [];
  let selectedIndex = 0;

  function hidePanel() {
    panel.hidden = true;
    panel.replaceChildren();
    visibleCommands = [];
    selectedIndex = 0;
  }

  function getCommandContext() {
    const value = messageInput.value;
    const slashIndex = value.lastIndexOf("/");

    if (slashIndex < 0) {
      return null;
    }

    if (slashIndex > 0 && !/\s/.test(value.charAt(slashIndex - 1))) {
      return null;
    }

    const query = value.slice(slashIndex).trim();

    if (!query.startsWith("/") || /\s/.test(query)) {
      return null;
    }

    return {
      prefix: value.slice(0, slashIndex).trimEnd(),
      query
    };
  }

    function executeCommand(item) {
    if (!item) {
      return;
    }

    const context = getCommandContext();

    if (context && context.prefix) {
      messageInput.value = `${context.prefix} ${item.inlinePrompt}`;
    } else {
      messageInput.value = item.prompt;
    }

    messageInput.dispatchEvent(new Event("input", { bubbles: true }));
    hidePanel();
    messageInput.focus();

    if (typeof chatForm.requestSubmit === "function") {
      chatForm.requestSubmit();
    }
    }

    function renderPanel() {
      const context = getCommandContext();

    if (!context) {
      hidePanel();
      return;
    }

    visibleCommands = commands.filter(item =>
      item.command.startsWith(context.query.toLowerCase())
    );

    if (visibleCommands.length === 0) {
      hidePanel();
      return;
    }

    selectedIndex = Math.min(selectedIndex, visibleCommands.length - 1);
    panel.replaceChildren();

    visibleCommands.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "pratik-yol-item";
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", String(index === selectedIndex));

      if (index === selectedIndex) {
        button.classList.add("is-selected");
      }

      const command = document.createElement("span");
      command.className = "pratik-yol-command";
      command.textContent = item.command;

      const detail = document.createElement("span");
      detail.className = "pratik-yol-detail";

      const title = document.createElement("span");
      title.className = "pratik-yol-title";
      title.textContent = item.title;

      const description = document.createElement("span");
      description.className = "pratik-yol-description";
      description.textContent = item.description;

      detail.append(title, description);
      button.append(command, detail);
      button.addEventListener("click", () => executeCommand(item));
      panel.appendChild(button);
    });

    panel.hidden = false;
  }

  function moveSelection(direction) {
    if (panel.hidden || visibleCommands.length === 0) {
      return;
    }

    selectedIndex = (
      selectedIndex + direction + visibleCommands.length
    ) % visibleCommands.length;
    renderPanel();
  }

  messageInput.addEventListener("input", renderPanel);

  messageInput.addEventListener("keydown", event => {
    if (panel.hidden || visibleCommands.length === 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      event.stopImmediatePropagation();
      moveSelection(1);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      event.stopImmediatePropagation();
      moveSelection(-1);
      return;
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.stopImmediatePropagation();
      executeCommand(visibleCommands[selectedIndex]);
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      event.stopImmediatePropagation();
      hidePanel();
    }
  });

  document.addEventListener("pointerdown", event => {
    if (event.target === messageInput || panel.contains(event.target)) {
      return;
    }
    hidePanel();
  });
})();

// PRATIK YOLLAR: BITIS
