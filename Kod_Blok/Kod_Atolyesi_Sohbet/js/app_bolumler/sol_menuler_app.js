// SOL MENULER JS: BASLANGIC

const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.getElementById("sidebarToggle");
const projectButton = document.getElementById("projectButton");
const projectMenu = document.getElementById("projectMenu");
const newProjectButton = document.getElementById("newProjectButton");
const openProjectButton = document.getElementById("openProjectButton");
const activeProject = document.getElementById("activeProject");
const activeProjectName = document.getElementById("activeProjectName");
const activeProjectPathLabel = document.getElementById("activeProjectPath");
const sidebarResizer = document.getElementById("sidebarResizer");

let sidebarOpenWidth = 240;
let resizingSidebar = false;
let activeProjectPath = "";

const SIDEBAR_MIN_WIDTH = 150;
const SIDEBAR_MAX_WIDTH = 520;

// SOL PANEL GENISLIGI: BASLANGIC
function clampSidebarWidth(width) {
  const viewportLimit = Math.max(
    SIDEBAR_MIN_WIDTH,
    Math.floor(window.innerWidth * 0.55)
  );

  return Math.max(
    SIDEBAR_MIN_WIDTH,
    Math.min(
      Number(width) || 180,
      SIDEBAR_MAX_WIDTH,
      viewportLimit
    )
  );
}

function applySidebarWidth(width) {
  sidebarOpenWidth = clampSidebarWidth(width);

  appShell.style.setProperty(
    "--sidebar-open-width",
    `${sidebarOpenWidth}px`
  );
}
// SOL PANEL GENISLIGI: BITIS

// PROJE GOSTERIMI: BASLANGIC
function showActiveProject(path, startsProjectMethod) {
  const projectPath = String(path || "").trim();

  if (!projectPath) {
    return;
  }

  const cleanPath = projectPath.replace(/[\\/]+$/, "");
  const parts = cleanPath.split(/[\\/]/);
  const projectName = parts[parts.length - 1] || cleanPath;

  activeProjectPath = projectPath;

  activeProjectName.textContent = projectName;
  activeProjectPathLabel.textContent = projectPath;
  activeProject.hidden = false;

  if (startsProjectMethod) {
    projectMenu.hidden = false;
    projectButton.setAttribute("aria-expanded", "true");

    syncSidebarActiveState(true);
    setWaiting(true);
  } else {
    projectMenu.hidden = true;
    projectButton.setAttribute("aria-expanded", "false");

    syncSidebarActiveState(false);
  }
}
// PROJE GOSTERIMI: BITIS

// SOL MENU AKTIF DURUMU: BASLANGIC
function syncSidebarActiveState(projectOpen = false) {
  const historyOpen = currentView === "history";
  const filesOpen = currentView === "files";
  const recordsOpen = currentView === "records";
  const chatOpen = currentView === "chat";

  projectButton.classList.toggle("active", projectOpen);

  historyButton.classList.toggle(
    "active",
    !projectOpen && historyOpen
  );

  if (fileButton) {
    fileButton.classList.toggle(
      "active",
      !projectOpen && filesOpen
    );
  }

  if (recordsButton) {
    recordsButton.classList.toggle(
      "active",
      !projectOpen && recordsOpen
    );
  }

  chatButton.classList.toggle(
    "active",
    !projectOpen && chatOpen
  );
}
// SOL MENU AKTIF DURUMU: BITIS

// PROJE MENUSU: BASLANGIC
function closeProjectMenu() {
  projectMenu.hidden = true;
  projectButton.setAttribute("aria-expanded", "false");

  syncSidebarActiveState(false);
}

function setSidebarOpen(opened) {
  appShell.classList.toggle("sidebar-open", opened);

  sidebarToggle.setAttribute(
    "aria-expanded",
    String(opened)
  );

  sidebarToggle.title = opened
    ? "Menüyü kapat"
    : "Menüyü aç";

  if (!opened) {
    closeProjectMenu();
  }
}

// Sol panel yalnız G düğmesi ile açılır ve kapanır.
sidebarToggle.addEventListener("click", () => {
  setSidebarOpen(
    !appShell.classList.contains("sidebar-open")
  );
});

projectButton.addEventListener("click", () => {
  const opened = projectMenu.hidden;

  projectMenu.hidden = !opened;

  projectButton.setAttribute(
    "aria-expanded",
    String(opened)
  );

  syncSidebarActiveState(opened);
});

newProjectButton.addEventListener("click", () => {
  closeProjectMenu();

  if (
    !bridge ||
    typeof bridge.start_new_project !== "function"
  ) {
    statusNote.textContent =
      "Yeni proje bağlantısı henüz hazır değil";

    return;
  }

  bridge.start_new_project();
});

openProjectButton.addEventListener("click", () => {
  closeProjectMenu();

  if (
    !bridge ||
    typeof bridge.select_project_folder !== "function"
  ) {
    statusNote.textContent =
      "Proje seçici henüz hazır değil";

    return;
  }

  bridge.select_project_folder();
});
// PROJE MENUSU: BITIS

// SOL PANEL BOYUTLANDIRMA: BASLANGIC
sidebarResizer.addEventListener(
  "pointerdown",
  event => {
    if (
      !appShell.classList.contains("sidebar-open")
    ) {
      return;
    }

    event.preventDefault();

    resizingSidebar = true;

    appShell.classList.add("sidebar-resizing");

    sidebarResizer.setPointerCapture(
      event.pointerId
    );
  }
);

sidebarResizer.addEventListener(
  "pointermove",
  event => {
    if (!resizingSidebar) {
      return;
    }

    const shellLeft =
      appShell.getBoundingClientRect().left;

    applySidebarWidth(
      event.clientX - shellLeft
    );
  }
);

function finishSidebarResize(event) {
  if (!resizingSidebar) {
    return;
  }

  resizingSidebar = false;

  appShell.classList.remove(
    "sidebar-resizing"
  );

  if (
    sidebarResizer.hasPointerCapture(
      event.pointerId
    )
  ) {
    sidebarResizer.releasePointerCapture(
      event.pointerId
    );
  }
}

sidebarResizer.addEventListener(
  "pointerup",
  finishSidebarResize
);

sidebarResizer.addEventListener(
  "pointercancel",
  finishSidebarResize
);

window.addEventListener("resize", () => {
  applySidebarWidth(sidebarOpenWidth);
});

applySidebarWidth(sidebarOpenWidth);
// SOL PANEL BOYUTLANDIRMA: BITIS

// SOL MENULER JS: BITIS
