// MARKDOWN RENDER: BAŞLANGIÇ

function splitMarkdownTableRow(row) {
  let source = String(row || "").trim();
  if (source.startsWith("|")) {
    source = source.slice(1);
  }
  if (source.endsWith("|")) {
    source = source.slice(0, -1);
  }

  const cells = [];
  let current = "";
  let inCode = false;

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (char === "\\" && (next === "|" || next === "\\")) {
      current += next;
      index += 1;
      continue;
    }

    if (char === "`") {
      inCode = !inCode;
      current += char;
      continue;
    }

    if (char === "|" && !inCode) {
      cells.push(current.trim());
      current = "";
      continue;
    }

    current += char;
  }

  cells.push(current.trim());
  return cells;
}

function isMarkdownTableDivider(cells) {
  return Array.isArray(cells)
    && cells.length > 0
    && cells.every(cell => /^:?-{3,}:?$/.test(String(cell || "").trim()));
}

function parseMarkdownHeading(line) {
  const match = String(line || "").match(/^\s{0,3}(#{1,4})\s+(.+?)\s*#*\s*$/);
  if (!match) {
    return null;
  }

  return {
    level: match[1].length,
    text: match[2].trim()
  };
}

function isMarkdownSeparator(line) {
  return /^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$/.test(String(line || ""));
}

function appendInlineMarkdown(container, text) {
  const source = String(text || "");
  const tokenPattern = /(`[^`\n]+`|\*\*\*[^*\n]+\*\*\*|___[^_\n]+___|\*\*[^*\n]+\*\*|__[^_\n]+__|~~[^~\n]+~~|\*[^*\n]+\*|_[^_\n]+_)/g;
  let cursor = 0;
  let match = null;

  while ((match = tokenPattern.exec(source)) !== null) {
    if (match.index > cursor) {
      container.appendChild(document.createTextNode(source.slice(cursor, match.index)));
    }

    const token = match[0];
    let element = null;
    let content = token;

    if (token.startsWith("`")) {
      element = document.createElement("code");
      element.className = "markdown-inline-code";
      content = token.slice(1, -1);
    } else if (token.startsWith("***") || token.startsWith("___")) {
      element = document.createElement("strong");
      const emphasis = document.createElement("em");
      emphasis.textContent = token.slice(3, -3);
      element.appendChild(emphasis);
      content = null;
    } else if (token.startsWith("**") || token.startsWith("__")) {
      element = document.createElement("strong");
      content = token.slice(2, -2);
    } else if (token.startsWith("~~")) {
      element = document.createElement("del");
      content = token.slice(2, -2);
    } else {
      element = document.createElement("em");
      content = token.slice(1, -1);
    }

    if (content !== null) {
      element.textContent = content;
    }
    container.appendChild(element);
    cursor = match.index + token.length;
  }

  if (cursor < source.length) {
    container.appendChild(document.createTextNode(source.slice(cursor)));
  }
}

function markdownTableAlignment(dividerCell) {
  const value = String(dividerCell || "").trim();
  if (value.startsWith(":") && value.endsWith(":")) {
    return "center";
  }
  if (value.endsWith(":")) {
    return "right";
  }
  return "left";
}

function createMarkdownTable(headerCells, dividerCells, rowLines) {
  const wrapper = document.createElement("div");
  wrapper.className = "markdown-table-wrap";

  const table = document.createElement("table");
  table.className = "markdown-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const alignments = dividerCells.map(markdownTableAlignment);

  headerCells.forEach((cellText, index) => {
    const cell = document.createElement("th");
    cell.className = `align-${alignments[index] || "left"}`;
    appendInlineMarkdown(cell, cellText);
    headRow.appendChild(cell);
  });

  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rowLines.forEach(line => {
    const values = splitMarkdownTableRow(line);
    const row = document.createElement("tr");

    headerCells.forEach((_header, index) => {
      const cell = document.createElement("td");
      cell.className = `align-${alignments[index] || "left"}`;
      appendInlineMarkdown(cell, values[index] || "");
      row.appendChild(cell);
    });

    tbody.appendChild(row);
  });

  table.appendChild(tbody);
  wrapper.appendChild(table);
  return wrapper;
}

function isMarkdownTableStart(lines, index) {
  if (index + 1 >= lines.length || !String(lines[index] || "").includes("|")) {
    return false;
  }

  const headerCells = splitMarkdownTableRow(lines[index]);
  const dividerCells = splitMarkdownTableRow(lines[index + 1]);
  return headerCells.length > 1
    && headerCells.length === dividerCells.length
    && isMarkdownTableDivider(dividerCells);
}

function parseMarkdownListLine(line) {
  const match = String(line || "").match(/^(\s*)([-+*]|\d+[.)])\s+(.*)$/);
  if (!match) {
    return null;
  }

  return {
    indent: match[1].replace(/\t/g, "    ").length,
    ordered: /^\d/.test(match[2]),
    text: match[3]
  };
}

function isMarkdownListLine(line) {
  return Boolean(parseMarkdownListLine(line));
}

function createMarkdownListItem(info) {
  let itemText = info.text;
  const item = document.createElement("li");
  const taskMatch = !info.ordered ? itemText.match(/^\[([ xX])\]\s+(.*)$/) : null;

  if (taskMatch) {
    item.classList.add("markdown-task-item");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.className = "markdown-task-box";
    box.checked = taskMatch[1].toLowerCase() === "x";
    box.setAttribute("aria-label", taskMatch[2]);
    item.appendChild(box);
    itemText = taskMatch[2];
  }

  appendInlineMarkdown(item, itemText);
  return item;
}

function appendMarkdownList(container, lines, startIndex) {
  const first = parseMarkdownListLine(lines[startIndex]);
  if (!first) {
    return startIndex;
  }

  const baseIndent = first.indent;
  const ordered = first.ordered;
  const list = document.createElement(ordered ? "ol" : "ul");
  list.className = "markdown-list";

  let index = startIndex;
  let lastItem = null;

  while (index < lines.length) {
    const info = parseMarkdownListLine(lines[index]);
    if (!info || info.indent < baseIndent) {
      break;
    }

    if (info.indent === baseIndent && info.ordered !== ordered) {
      break;
    }

    if (info.indent > baseIndent) {
      if (!lastItem) {
        break;
      }
      const nextIndex = appendMarkdownList(lastItem, lines, index);
      if (nextIndex === index) {
        break;
      }
      index = nextIndex;
      continue;
    }

    lastItem = createMarkdownListItem(info);
    list.appendChild(lastItem);
    index += 1;
  }

  container.appendChild(list);
  return index;
}

function isMarkdownBlockStart(lines, index) {
  const line = String(lines[index] || "");
  return Boolean(
    parseMarkdownHeading(line)
    || isMarkdownSeparator(line)
    || isMarkdownTableStart(lines, index)
    || /^\s{0,3}>\s?/.test(line)
    || isMarkdownListLine(line)
  );
}

function appendMarkdownParagraph(container, lines) {
  const paragraph = document.createElement("p");
  paragraph.className = "markdown-paragraph";

  lines.forEach((line, index) => {
    if (index > 0) {
      paragraph.appendChild(document.createElement("br"));
    }
    appendInlineMarkdown(paragraph, line);
  });

  container.appendChild(paragraph);
}

function appendAssistantMarkdown(container, text) {
  const lines = String(text || "").replace(/\r\n?/g, "\n").split("\n");
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const heading = parseMarkdownHeading(line);
    if (heading) {
      const element = document.createElement(`h${heading.level}`);
      element.className = `markdown-heading markdown-h${heading.level}`;
      appendInlineMarkdown(element, heading.text);
      container.appendChild(element);
      index += 1;
      continue;
    }

    if (isMarkdownSeparator(line)) {
      const separator = document.createElement("hr");
      separator.className = "markdown-separator";
      container.appendChild(separator);
      index += 1;
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      const headerCells = splitMarkdownTableRow(lines[index]);
      const dividerCells = splitMarkdownTableRow(lines[index + 1]);
      const rowLines = [];
      index += 2;

      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
        rowLines.push(lines[index]);
        index += 1;
      }

      container.appendChild(createMarkdownTable(headerCells, dividerCells, rowLines));
      continue;
    }

    if (/^\s{0,3}>\s?/.test(line)) {
      const quote = document.createElement("blockquote");
      quote.className = "markdown-quote";

      while (index < lines.length && /^\s{0,3}>\s?/.test(lines[index])) {
        const quoteLine = lines[index].replace(/^\s{0,3}>\s?/, "");
        if (quote.childNodes.length > 0) {
          quote.appendChild(document.createElement("br"));
        }
        appendInlineMarkdown(quote, quoteLine);
        index += 1;
      }

      container.appendChild(quote);
      continue;
    }

    if (isMarkdownListLine(line)) {
      index = appendMarkdownList(container, lines, index);
      continue;
    }

    const paragraphLines = [line];
    index += 1;
    while (
      index < lines.length
      && lines[index].trim()
      && !isMarkdownBlockStart(lines, index)
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }

    appendMarkdownParagraph(container, paragraphLines);
  }

}

// MARKDOWN RENDER: BİTİŞ
