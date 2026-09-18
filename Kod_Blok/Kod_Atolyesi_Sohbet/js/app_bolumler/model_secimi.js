(() => {
    const selector = document.getElementById("modelSecici");
    const trigger = document.getElementById("modelSecimTrigger");
    const menu = document.getElementById("modelSecimMenu");
    const triggerLabel = document.getElementById("modelSecimTriggerLabel");
    const triggerIcon = document.getElementById("modelSecimTriggerIcon");
    const options = Array.from(
        document.querySelectorAll(".model-secim-option[data-model-mode]")
    );

    if (!selector || !trigger || !menu || !triggerLabel || !triggerIcon) {
        return;
    }

    const modeLabels = {
        auto: "Otomatik",
        normal: "Normal",
        kod: "Kod",
    };

    let activeMode = "auto";

    function closeMenu() {
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
    }

    function syncModeToBridge(mode) {
        if (
            typeof bridge !== "undefined"
            && bridge
            && typeof bridge.set_model_mode === "function"
        ) {
            bridge.set_model_mode(mode);
            return true;
        }
        return false;
    }

    function updateTrigger(mode, sourceOption) {
        triggerLabel.textContent = modeLabels[mode] || modeLabels.auto;
        triggerIcon.className = `model-secim-trigger-icon model-secim-trigger-${mode}`;

        const icon = sourceOption?.querySelector(".model-secim-icon");
        if (icon) {
            triggerIcon.innerHTML = icon.innerHTML;
        }
    }

    function setMode(mode, notifyBridge = true) {
        if (!Object.hasOwn(modeLabels, mode)) {
            mode = "auto";
        }

        activeMode = mode;
        const selectedOption = options.find(
            (option) => option.dataset.modelMode === mode
        );

        options.forEach((option) => {
            option.classList.toggle(
                "is-selected",
                option.dataset.modelMode === mode
            );
        });

        updateTrigger(mode, selectedOption);
        closeMenu();

        if (notifyBridge) {
            syncModeToBridge(activeMode);
        }
    }

    trigger.addEventListener("click", (event) => {
        event.stopPropagation();
        if (menu.hidden) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    options.forEach((option) => {
        option.addEventListener("click", (event) => {
            event.stopPropagation();
            setMode(option.dataset.modelMode || "auto");
        });
    });

    document.addEventListener("click", (event) => {
        if (!selector.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeMenu();
        }
    });

    setMode("auto", false);

    let bridgeSyncAttempts = 0;
    const bridgeSyncTimer = window.setInterval(() => {
        bridgeSyncAttempts += 1;
        if (syncModeToBridge(activeMode) || bridgeSyncAttempts >= 40) {
            window.clearInterval(bridgeSyncTimer);
        }
    }, 250);
})();
