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

    python python/medium_export.py article-01-methodology.md
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


def render_table(lines, out: Path, max_chars: int = 34):
    """Render a Markdown table as a PNG that stays readable on a phone.

    Medium scales images to the column width -- about 350 px on a phone. A
    first version sized the image to the longest row, which for tables with
    long descriptions meant 2,600 px and unreadable type. Now the image has a
    fixed width and a large font, and cells wrap: numeric columns keep their
    width, the widest text column takes the rest of `max_chars`.
    """
    import textwrap
    header, align, body = parse_table(lines)
    ncol = len(header)
    cells = [[strip_md(c) for c in r] + [""] * (ncol - len(r))
             for r in [header] + body]
    bold = [[r == 0 or (c.startswith("**") if c else False)
             for c in row] for r, row in enumerate([header] + body)]
    natural = [max(len(r[i]) for r in cells) for i in range(ncol)]
    # other columns wrap at 12 characters at most; the first (label) column
    # gets whatever is left, but never less than 18
    widths = [natural[0]] + [min(n, 10) for n in natural[1:]]
    widths[0] = max(14, min(natural[0], max_chars - sum(widths[1:]) - 2 * ncol))
    wrapped = [[textwrap.wrap(c, widths[i], break_long_words=False,
                              break_on_hyphens=False) or [""]
                for i, c in enumerate(r)]
               for r in cells]
    heights = [max(len(c) for c in r) for r in wrapped]
    col_w = [w + 2 for w in widths]
    total = sum(col_w)
    line_h = 0.36
    fig_w = 4.4
    fig_h = line_h * sum(0.82 * h + 0.55 for h in heights) + 0.2
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=220)
    fig.patch.set_facecolor(P["surface"])
    ax.set_axis_off()
    rows_h = [0.82 * h + 0.55 for h in heights]
    ax.set_xlim(0, total); ax.set_ylim(sum(rows_h), 0)
    ax.add_patch(plt.Rectangle((0, 0), total, rows_h[0], color=P["head"], lw=0))
    y = 0
    for r, row in enumerate(wrapped):
        x = 0
        for c in range(ncol):
            txt = "\n".join(row[c])
            kw = dict(fontsize=12, color=P["ink"], va="center",
                      linespacing=1.25,
                      fontweight="bold" if bold[r][c] else "normal")
            yc = y + rows_h[r] / 2
            if align[c] == "right":
                ax.text(x + col_w[c] - 1.0, yc, txt, ha="right", multialignment="right", **kw)
            else:
                ax.text(x + 0.8, yc, txt, ha="left", **kw)
            x += col_w[c]
        y += rows_h[r]
        if r > 0:
            ax.plot([0, total], [y, y], color=P["grid"], lw=0.8)
    fig.tight_layout(pad=0.25)
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
            # consecutive "> " lines are one paragraph, as in Markdown; the
            # first version formatted each line on its own, so italics that
            # span lines showed their asterisks
            out.append("<blockquote><p>" + inline(" ".join(buf))
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
    write_preview(body, outdir, src.stem)


def write_preview(body, outdir, stem):
    """preview.html: roughly how the article reads on Medium -- Medium-like
    typography, images inlined as data URIs so the file works anywhere.
    Not for pasting; the paste version is <stem>.html."""
    import base64
    def inline_img(m):
        f = outdir / m.group(1)
        if not f.exists():
            return m.group(0)
        b64 = base64.b64encode(f.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}"'
    body = re.sub(r'<p style="border:2px dashed[^"]*"[^>]*>.*?</p>', "", body)
    body = re.sub(r'<img src="([^"]+)"', inline_img, body)
    css = """
    body{margin:0;background:#fff;color:#242424}
    main{max-width:680px;margin:0 auto;padding:48px 24px 96px}
    h1{font:700 42px/1.2 -apple-system,'Helvetica Neue',sans-serif;
       letter-spacing:-0.016em;margin:0 0 12px}
    h3:first-of-type{font:400 22px/1.4 -apple-system,'Helvetica Neue',sans-serif;
       color:#6b6b6b;margin:0 0 32px}
    h2{font:700 24px/1.3 -apple-system,'Helvetica Neue',sans-serif;
       margin:48px 0 8px}
    h3{font:700 20px/1.3 -apple-system,'Helvetica Neue',sans-serif;margin:36px 0 4px}
    p,li{font:400 20px/1.6 Charter,'Bitstream Charter','Sitka Text',Georgia,serif;
       letter-spacing:-0.003em;margin:0 0 28px}
    blockquote{border-left:3px solid #242424;margin:0 0 28px;padding-left:20px}
    blockquote p{font-style:italic}
    pre{background:#f2f2f2;padding:20px;border-radius:4px;overflow-x:auto;
       font:14px/1.5 Menlo,monospace;margin:0 0 28px}
    code{font:15px Menlo,monospace;background:#f2f2f2;padding:2px 4px}
    pre code{background:none;padding:0}
    img{max-width:100%;display:block;margin:12px auto 36px}
    hr{border:0;text-align:center;margin:40px 0}
    hr:after{content:"...";font:28px serif;letter-spacing:1em;color:#242424}
    a{color:inherit}
    .byline{font:14px -apple-system,sans-serif;color:#6b6b6b;margin:0 0 40px}
    """
    body = body.replace("</h3>", "</h3><p class='byline'>Marcel Mueller · "
                        "Preview, not the published layout</p>", 1)
    page = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{stem} — preview</title><style>{css}</style></head>"
            f"<body><main>{body}</main></body></html>")
    (outdir / "preview.html").write_text(page)
    print(f"wrote {outdir}/preview.html")


if __name__ == "__main__":
    main()
