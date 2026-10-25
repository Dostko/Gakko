// KOD RENDER: BAŞLANGIÇ

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeCodeLanguage(language, code) {
  const raw = String(language || "").trim().toLowerCase();
  const aliases = {
    js: "JavaScript",
    javascript: "JavaScript",
    ts: "TypeScript",
    typescript: "TypeScript",
    py: "Python",
    python: "Python",
    html: "HTML",
    htm: "HTML",
    css: "CSS",
    json: "JSON",
    bash: "Bash",
    sh: "Bash",
    shell: "Bash",
    powershell: "PowerShell",
    ps1: "PowerShell",
    text: "Metin",
    txt: "Metin"
  };

  if (aliases[raw]) {
    return aliases[raw];
  }

  if (raw) {
    return raw.toUpperCase();
  }

  const sample = String(code || "").trim();
  if (/^(?:<!doctype\s+html|<html\b|<[a-z][\s\S]*>)/i.test(sample)) {
    return "HTML";
  }
  if (/\b(?:const|let|var|function|=>|document\.)\b/.test(sample)) {
    return "JavaScript";
  }
  if (/^(?:from\s+\S+\s+import|import\s+\S+|def\s+\w+|class\s+\w+)/m.test(sample)) {
    return "Python";
  }
  if (/^[.#]?[\w-]+[^\n{]*\{[\s\S]*:[^;{}]+;?/m.test(sample)) {
    return "CSS";
  }
  return "Kod";
}

function highlightCode(code, language) {
  const source = String(code || "");
  const displayLanguage = normalizeCodeLanguage(language, source);
  const keywordPattern = /\b(?:async|await|break|case|catch|class|const|continue|def|del|do|elif|else|except|export|extends|false|finally|for|from|function|if|import|in|interface|let|new|null|pass|return|switch|throw|true|try|var|while|with|yield|None|True|False)\b/;
  const tokenPattern = /(<!--[\s\S]*?-->|\/\*[\s\S]*?\*\/|\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|<\/?[A-Za-z][^>]*>|#[0-9a-fA-F]{3,8}\b|\b\d+(?:\.\d+)?\b|\b(?:async|await|break|case|catch|class|const|continue|def|del|do|elif|else|except|export|extends|false|finally|for|from|function|if|import|in|interface|let|new|null|pass|return|switch|throw|true|try|var|while|with|yield|None|True|False)\b)/g;

  let html = "";
  let cursor = 0;

  source.replace(tokenPattern, (token, _match, offset) => {
    html += escapeHtml(source.slice(cursor, offset));

    let className = "";
    if (/^(?:<!--|\/\*|\/\/|#(?![0-9a-fA-F]{3,8}\b))/.test(token)) {
      className = "syn-comment";
    } else if (/^["'`]/.test(token)) {
      className = "syn-string";
    } else if (/^<\/?[A-Za-z]/.test(token)) {
      className = "syn-tag";
    } else if (/^#[0-9a-fA-F]{3,8}\b/.test(token) || /^\d/.test(token)) {
      className = "syn-number";
    } else if (keywordPattern.test(token)) {
      className = "syn-keyword";
    }

    html += className
      ? `<span class="${className}">${escapeHtml(token)}</span>`
      : escapeHtml(token);
    cursor = offset + token.length;
    return token;
  });

  html += escapeHtml(source.slice(cursor));
  return { html, displayLanguage };
}

async function copyCodeText(codeText, button) {
  let copied = false;

  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(codeText);
      copied = true;
    }
  } catch (error) {
    copied = false;
  }

  if (!copied) {
    const helper = document.createElement("textarea");
    helper.value = codeText;
    helper.setAttribute("readonly", "");
    helper.style.position = "fixed";
    helper.style.opacity = "0";
    document.body.appendChild(helper);
    helper.select();
    copied = document.execCommand("copy");
    helper.remove();
  }

  const oldText = button.textContent;
  button.textContent = copied ? "Kopyalandı" : "Kopyalanamadı";
  setTimeout(() => {
    button.textContent = oldText;
  }, 1400);
}

function isSvgCodeBlock(codeText, language) {
  const normalizedLanguage = String(language || "").trim().toLowerCase();
  const normalizedCode = String(codeText || "").trim();

  if (!/^<svg[\s>]/i.test(normalizedCode)) {
    return false;
  }

  return normalizedLanguage === "" || normalizedLanguage === "svg" || normalizedLanguage === "xml";
}

function createSvgPreview(svgText) {
  const image = document.createElement("img");
  image.className = "assistant-image";
  image.alt = "GAKKO SVG görseli";
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(String(svgText || "").trim())}`;
  enableImagePreview(image);
  image.addEventListener("error", () => image.remove());
  return image;
}

function createCodeBlock(codeText, language) {
  if (isSvgCodeBlock(codeText, language)) {
    return createSvgPreview(codeText);
  }

  const wrapper = document.createElement("div");
  wrapper.className = "code-block";

  const header = document.createElement("div");
  header.className = "code-block-header";

  const highlighted = highlightCode(codeText, language);
  const languageLabel = document.createElement("span");
  languageLabel.className = "code-language";
  languageLabel.textContent = highlighted.displayLanguage;

  const copyButton = document.createElement("button");
  copyButton.className = "code-copy-button";
  copyButton.type = "button";
  copyButton.textContent = "Kopyala";
  copyButton.addEventListener("click", () => copyCodeText(codeText, copyButton));

  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.innerHTML = highlighted.html;
  pre.appendChild(code);

  header.appendChild(languageLabel);
  header.appendChild(copyButton);
  wrapper.appendChild(header);
  wrapper.appendChild(pre);
  return wrapper;
}

// KOD RENDER: BİTİŞ
