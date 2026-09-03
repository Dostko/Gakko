from pathlib import Path


PROJECT_ROOT = Path(r"D:\Gakko")
YUVA_ROOT = PROJECT_ROOT / "GAKKO_YUVA"
CALISMA_YONTEMLERI_ROOT = YUVA_ROOT / "Calisma_Yontemleri"
MEVCUT_PROJE_YONTEMI = CALISMA_YONTEMLERI_ROOT / "mevcut_projeyi_baslat_incele.md"
YENI_PROJE_YONTEMI = CALISMA_YONTEMLERI_ROOT / "yeni_proje_olustur.md"


def list_project_directory(project_root, relative_path=""):
    root = Path(project_root).resolve()
    relative = str(relative_path or "").replace("\\", "/").strip("/")
    target = root.joinpath(*([part for part in relative.split("/") if part] or [])).resolve()

    if target != root and not target.is_relative_to(root):
        raise ValueError("Proje kökü dışındaki klasörler listelenemez.")

    if not target.exists() or not target.is_dir():
        raise ValueError("İstenen proje klasörü bulunamadı.")

    entries = []
    for entry in target.iterdir():
        try:
            is_directory = entry.is_dir()
        except OSError:
            continue

        entry_relative = entry.relative_to(root).as_posix()
        entries.append({
            "name": entry.name,
            "type": "directory" if is_directory else "file",
            "path": entry_relative,
        })

    entries.sort(key=lambda item: (item["type"] != "directory", item["name"].casefold()))

    return {
        "path": relative,
        "entries": entries,
    }


def format_attachment_reference(path):
    clean = str(path or "").strip().replace("\\", "/")
    if not clean:
        return ""
    return "@" + clean.replace(" ", "\\ ")


def attachment_display_name(path):
    clean = str(path or "").strip().replace("\\", "/").rstrip("/")
    if not clean:
        return ""
    return clean.rsplit("/", 1)[-1]


def build_attachment_prompt(message, file_paths):
    message = str(message or "").strip()
    references = [
        format_attachment_reference(path)
        for path in (file_paths or [])
        if str(path or "").strip()
    ]
    references = [reference for reference in references if reference]

    if not references:
        return message

    user_text = message or "Ekli dosyaları incele."
    attachment_block = "\n".join(f"- {reference}" for reference in references)
    return (
        f"{user_text}\n\n"
        "Ekli dosyalar:\n"
        f"{attachment_block}\n\n"
        "Bu ekli dosyaları yalnızca bu istek için bağlam olarak kullan; "
        "kullanıcı açıkça istemeden değiştirme."
    )


def build_attachment_history_message(message, file_paths):
    message = str(message or "").strip() or "Ekli dosyaları incele."
    names = [
        attachment_display_name(path)
        for path in (file_paths or [])
        if str(path or "").strip()
    ]
    names = [name for name in names if name]
    if not names:
        return message
    return f"{message}\n\nEkler: {', '.join(names)}"
