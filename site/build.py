# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown>=3.6"]
# ///
"""Build the documentation site from README.md and docs/*.md into site/dist.

    uv run site/build.py
    python -m http.server -d site/dist      # preview
"""
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "site" / "dist"
GITHUB = "https://github.com/majlisofai/mldlc-kit"

# (source, output folder, nav label, description)
PAGES = [
    ("README.md", "", "Overview", "A gated ML life cycle for new projects: skills for Claude Code and the mldlc command."),
    ("docs/lifecycle.md", "lifecycle", "Life cycle", "The gates, who decides each one, and how a change re-enters."),
    ("docs/adopting.md", "adopting", "Adopting", "Use mldlc in a new project, an existing repository, a monorepo and CI."),
    ("docs/evidence-contract.md", "evidence-contract", "Evidence contract", "The MLflow tags, metrics and files a project leaves for the gates."),
]

SYMBOL = (
    '<svg class="symbol" viewBox="0 0 64 64" width="32" height="32" role="img" aria-label="The Majlis of AI">'
    '<path d="M11.317 49.355 A27 27 0 1 1 52.683 49.355" fill="none" stroke="var(--ink)" stroke-width="6"/>'
    '<path d="M18.977 42.927 A17 17 0 1 1 45.023 42.927" fill="none" stroke="var(--ink)" stroke-width="6"/>'
    '<circle cx="32" cy="32" r="6" fill="#CC3A1C"/></svg>'
)

CSS = """
:root{--surface-100:#FFFFFF;--surface-200:#F5F5F5;--surface-300:#E6E6E6;--ink:#111111;--ink-muted:#5C5C5C;
--hairline:#D9D9D9;--border:#767676;--redline:#CC3A1C}
:root:not([data-theme="light"]){color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface-100:#121212;--surface-200:#1E1E1E;
--surface-300:#2A2A2A;--ink:#FFFFFF;--ink-muted:#B3B3B3;--hairline:#333333;--border:#8A8A8A;--redline:#FF7A5C}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--surface-100);color:var(--ink);font:400 16px/26px 'IBM Plex Sans',system-ui,sans-serif}
a{color:var(--ink);text-underline-offset:3px;text-decoration-thickness:1px}
a:hover{text-decoration-thickness:2px}
:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.wrap{max-width:1200px;margin:0 auto;padding:0 64px}
header.site{border-bottom:1px solid var(--hairline)}
header.site .wrap{display:flex;align-items:center;gap:24px;flex-wrap:wrap;padding-top:16px;padding-bottom:16px}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;font:500 13px/16px 'IBM Plex Sans',sans-serif;letter-spacing:.2em}
.brand .symbol{display:block}
nav{margin-left:auto;display:flex;gap:24px;flex-wrap:wrap}
nav a{font:600 13px/16px 'IBM Plex Sans Condensed','IBM Plex Sans',sans-serif;letter-spacing:.1em;text-transform:uppercase;
text-decoration:none;color:var(--ink-muted);padding:8px 0;display:inline-flex;align-items:center;gap:8px}
nav a:hover{color:var(--ink)}
nav a[aria-current="page"]{color:var(--ink)}
nav a[aria-current="page"]::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--redline)}
main{padding:64px 0 96px}
article{max-width:780px}
h1{font:300 48px/56px 'IBM Plex Sans',sans-serif;letter-spacing:-.01em;margin:0 0 32px}
h2{font:400 32px/40px 'IBM Plex Sans',sans-serif;margin:64px 0 16px}
h3{font:500 20px/28px 'IBM Plex Sans',sans-serif;margin:32px 0 8px}
p,ul,ol{margin:0 0 16px}
li{margin:0 0 4px}
hr{border:0;border-top:1px solid var(--hairline);margin:48px 0}
code{font:400 14px/22px 'IBM Plex Mono',ui-monospace,Menlo,monospace;background:var(--surface-200);padding:1px 4px}
pre{background:var(--surface-200);padding:16px 24px;overflow-x:auto;margin:0 0 24px}
pre code{background:none;padding:0}
img{max-width:100%;height:auto;display:block}
article img{margin:32px 0;border:1px solid var(--hairline)}
.table{overflow-x:auto;margin:0 0 24px}
table{border-collapse:collapse;width:100%;font-size:14px;line-height:22px}
th{background:var(--surface-300);text-align:left;font-weight:600}
th,td{padding:8px 12px;border-bottom:1px solid var(--hairline);vertical-align:top}
tbody tr:nth-child(even){background:var(--surface-200)}
footer.site{border-top:1px solid var(--hairline);padding:32px 0 48px;color:var(--ink-muted);font-size:14px}
footer.site .wrap{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
footer.site .tag{margin-right:auto}
footer.site a{color:var(--ink-muted)}
@media (max-width:1023px){.wrap{padding:0 32px}h1{font-size:40px;line-height:48px}}
@media (max-width:639px){.wrap{padding:0 16px}main{padding:32px 0 64px}h1{font-size:32px;line-height:40px}
h2{font-size:24px;line-height:32px;margin-top:48px}nav{margin-left:0;gap:16px}}
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="icon" href="/assets/brand/majlis-symbol.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap">
<style>{css}</style>
</head>
<body>
<header class="site"><div class="wrap">
<a class="brand" href="/" aria-label="mldlc-kit, home">{symbol}<span>MLDLC-KIT</span></a>
<nav aria-label="Documentation">{nav}</nav>
</div></header>
<main><div class="wrap"><article>
{body}
</article></div></main>
<footer class="site"><div class="wrap">
<span class="tag">Counsel for AI in regulated institutions.</span>
<a href="{github}">GitHub</a>
<a href="{github}/blob/main/LICENSE">MIT licence</a>
<span>The Majlis of AI</span>
</div></footer>
</body>
</html>
"""


def render(md_text: str) -> str:
    # The site has its own header and footer: drop the README's logo blocks.
    md_text = re.sub(r"<p align=\"center\">\s*<picture>.*?</picture>.*?</p>\s*", "", md_text, flags=re.S)
    md_text = re.sub(r"<picture>.*?</picture>\s*", "", md_text, flags=re.S)
    md_text = re.sub(r"\n---\s*\n*\Z", "\n", md_text)
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    html = re.sub(r"<table>.*?</table>", lambda m: f'<div class="table">{m.group(0)}</div>', html, flags=re.S)
    # Links between pages become clean URLs; assets move to /assets.
    html = re.sub(r'href="(?:docs/)?(lifecycle|adopting|evidence-contract)\.md"', r'href="/\1/"', html)
    html = html.replace('href="LICENSE"', f'href="{GITHUB}/blob/main/LICENSE"')
    html = re.sub(r'src="(?:docs/)?assets/', 'src="/assets/', html)
    return html


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(ROOT / "docs" / "assets", DIST / "assets")

    for src, folder, label, description in PAGES:
        body = render((ROOT / src).read_text())
        current = ' aria-current="page"'
        nav = "".join(
            f'<a href="/{f + "/" if f else ""}"{current if f == folder else ""}>{lbl}</a>'
            for _, f, lbl, _ in PAGES
        )
        h1 = re.search(r"<h1>(.*?)</h1>", body, flags=re.S)
        title = re.sub(r"<[^>]+>", "", h1.group(1)) if h1 else label
        page = HEAD.format(
            title=f"{title} · mldlc-kit" if folder else title,
            description=description,
            css=CSS,
            symbol=SYMBOL,
            nav=nav,
            body=body,
            github=GITHUB,
        )
        out = DIST / folder / "index.html" if folder else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)
        print(f"built {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
