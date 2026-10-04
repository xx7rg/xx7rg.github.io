from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import re


ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = [
    ROOT / "index.html",
    ROOT / "privacy-policy.html",
    ROOT / "terms-of-use.html",
    ROOT / "404.html",
]


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.references: list[tuple[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                self.references.append((attribute, value))


def validate_html(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    parser = DocumentParser()
    parser.feed(source)

    if not source.lstrip().lower().startswith("<!doctype html>"):
        errors.append(f"{path.name}: declaração <!doctype html> ausente")

    for attribute, reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme in {"http", "https", "mailto", "tel"}:
            continue

        if reference.startswith("#"):
            fragment = unquote(parsed.fragment)
            if fragment and fragment not in parser.ids:
                errors.append(f"{path.name}: âncora inexistente #{fragment}")
            continue

        local_path = unquote(parsed.path)
        if not local_path:
            continue

        target = ((ROOT / local_path.lstrip("/")) if local_path.startswith("/")
                  else (path.parent / local_path)).resolve()
        if target.is_dir():
            target = target / "index.html"
        if ROOT not in target.parents and target != ROOT:
            errors.append(f"{path.name}: caminho fora do projeto: {reference}")
        elif not target.exists():
            errors.append(
                f"{path.name}: destino local de {attribute} não existe: {reference}"
            )

    return errors


def validate_readme() -> list[str]:
    errors: list[str] = []
    source = (ROOT / "README.md").read_text(encoding="utf-8")
    references = re.findall(r"(?:src=\"|\]\()([^\")]+)", source)

    for reference in references:
        parsed = urlparse(reference)
        if parsed.scheme in {"http", "https", "mailto"} or reference.startswith("#"):
            continue
        target = (ROOT / unquote(parsed.path)).resolve()
        if not target.exists():
            errors.append(f"README.md: destino local não existe: {reference}")

    return errors


def main() -> int:
    errors: list[str] = []
    for html_file in HTML_FILES:
        if not html_file.exists():
            errors.append(f"arquivo obrigatório ausente: {html_file.name}")
            continue
        errors.extend(validate_html(html_file))
    errors.extend(validate_readme())

    if errors:
        for error in errors:
            print(f"ERRO: {error}")
        return 1

    print("OK: HTML, imagens, links locais e ancoras validados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
