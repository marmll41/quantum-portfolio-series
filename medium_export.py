"""
Prepare an article for Medium.

Medium's editor has no tables, and pasting Markdown does not work. This
script turns an article into

  medium/<stem>/<stem>.html     open in a browser, select all, paste into
                                Medium: headings, bold, italics, quotes,
                                code blocks and links survive the paste
  medium/<stem>/table-N.png     every Markdown table rendered as an image in
                                the style of the series' charts
  medium/<stem>/*.png           copies of the charts the article embeds

Images do not travel through the clipboard into Medium; the HTML marks each
spot with a grey box naming the file to upload there.

    python medium_export.py article-01-methodology.md
"""

from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Same light tokens as the charts.
P = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#d8d7d2",
         head="#efeee9")


# --------------------------------------------------------------------------
# Tables -> PNG
# --------------------------------------------------------------------------

def parse_table(lines):
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    header, align_row, body = rows[0], rows[1], rows[2:]
    align = ["right" if a.endswith(":") and not a.startswith(":") else "left"
             for a in align_row]
    return header, align, body


def strip_md(s):
    return s.replace("**", "").replace("`", "").replace("*", "")


def render_table(lines, out: Path):
    header, align, body = parse_table(lines)
    ncol = len(header)
    cells = [header] + body
    # column widths from text length, in character units
    widths = [max(len(strip_md(r[i])) if i < len(r) else 0 for r in cells) + 3
              for i in range(ncol)]
    total = sum(widths)
    row_h, fig_w = 0.42, min(14.0, max(7.0, total * 0.105))
    fig_h = row_h * (len(cells) + 0.4)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
    fig.patch.set_facecolor(P["surface"])
    ax.set_axis_off()
    ax.set_xlim(0, total); ax.set_ylim(len(cells), 0)
    ax.add_patch(plt.Rectangle((0, 0), total, 1, color=P["head"], lw=0))
    for r, row in enumerate(cells):
        x = 0
        for c in range(ncol):
            text = row[c] if c < len(row) else ""
            bold = r == 0 or text.startswith("**")
            t = strip_md(text)
            if align[c] == "right":
                ax.text(x + widths[c] - 1.2, r + 0.5, t, ha="right",
                        va="center", fontsize=11, color=P["ink"],
                        fontweight="bold" if bold else "normal")
            else:
                ax.text(x + 1.0, r + 0.5, t, ha="left", va="center",
                        fontsize=11, color=P["ink"] if c == 0 or r == 0
                        else P["ink"],
                        fontweight="bold" if bold else "normal")
            x += widths[c]
        if r > 0:
            ax.plot([0, total], [r, r], color=P["grid"], lw=0.8)
    fig.tight_layout(pad=0.3)
    fig.savefig(out, facecolor=P["surface"])
    plt.close(fig)


# --------------------------------------------------------------------------
# Minimal Markdown -> HTML (only what the articles use)
# --------------------------------------------------------------------------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def placeholder(name, alt=""):
    label = html.escape(alt) + " — " if alt else ""
    return (f'<p style="border:2px dashed #999;padding:12px;color:#555;'
            f'font-family:sans-serif">[Bild hochladen / upload image: '
            f'<b>{html.escape(name)}</b>] {label}</p>'
            f'<p><img src="{html.escape(name)}" style="max-width:100%"></p>')


def convert(md: str, outdir: Path, src_dir: Path):
    lines = md.split("\n")
    out, i, ntab = [], 0, 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            code = html.escape("\n".join(lines[i + 1:j]))
            out.append(f"<pre><code>{code}</code></pre>")
            i = j + 1
            continue
        if line.startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            ntab += 1
            name = f"table-{ntab}.png"
            render_table(lines[i:j], outdir / name)
            out.append(placeholder(name, "Tabelle / table"))
            i = j
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if m:
            alt, src = m.groups()
            if (src_dir / src).exists():
                shutil.copy(src_dir / src, outdir / Path(src).name)
            out.append(placeholder(Path(src).name, alt))
            i += 1
            continue
        m = re.match(r"(#{1,4}) (.*)", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        if line.startswith(">"):
            j = i
            buf = []
            while j < len(lines) and lines[j].startswith(">"):
                buf.append(lines[j].lstrip(">").strip())
                j += 1
            out.append("<blockquote><p>" + "<br>".join(inline(b) for b in buf)
                       + "</p></blockquote>")
            i = j
            continue
        if re.match(r"(- |\d+\. )", line):
            j, items = i, []
            ordered = bool(re.match(r"\d+\. ", line))
            while j < len(lines) and lines[j].strip():
                if re.match(r"(- |\d+\. )", lines[j]):
                    items.append(re.sub(r"^(- |\d+\. )", "", lines[j]))
                else:
                    items[-1] += " " + lines[j].strip()
                j += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>"
                                             for t in items) + f"</{tag}>")
            i = j
            continue
        if not line.strip():
            i += 1
            continue
        j, buf = i, []
        while (j < len(lines) and lines[j].strip()
               and not re.match(r"(#{1,4} |```|\||>|!\[|- |\d+\. |---$)",
                                lines[j])):
            buf.append(lines[j].strip())
            j += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")
        i = j
    return "\n".join(out), ntab


def main():
    src = Path(sys.argv[1])
    outdir = Path("medium") / src.stem
    outdir.mkdir(parents=True, exist_ok=True)
    body, ntab = convert(src.read_text(), outdir, src.parent)
    page = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{src.stem}</title><style>body{{max-width:720px;"
            f"margin:40px auto;font-family:Georgia,serif;line-height:1.55;"
            f"padding:0 16px}}pre{{background:#f4f4f2;padding:12px;"
            f"overflow-x:auto}}blockquote{{border-left:3px solid #999;"
            f"margin-left:0;padding-left:16px;color:#333}}</style></head>"
            f"<body>{body}</body></html>")
    (outdir / f"{src.stem}.html").write_text(page)
    print(f"wrote {outdir}/{src.stem}.html  ({ntab} tables rendered)")


if __name__ == "__main__":
    main()
