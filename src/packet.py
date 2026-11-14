"""Labelling packet: items 1-30 in labelling-page order, with links, evidence and the factual
code map for each. Observation files (AI opinions) are deliberately excluded so labels stay blind."""
import csv, json, re, sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
                                Preformatted, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

R = '/home/user/mcp-drift'
FD = '/usr/share/fonts/truetype/dejavu/'
pdfmetrics.registerFont(TTFont('Sans', FD + 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('Sans-B', FD + 'DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Mono', FD + 'DejaVuSansMono.ttf'))
from reportlab.lib.fonts import addMapping
addMapping('Sans', 0, 0, 'Sans'); addMapping('Sans', 1, 0, 'Sans-B'); addMapping('Sans', 0, 1, 'Sans'); addMapping('Sans', 1, 1, 'Sans-B')

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUT = f'{R}/validation/labeling_packet_1-{N}.pdf'
INK, MUTED, ACC, LINE, SOFT = '#1f2933', '#52606d', '#1d4e89', '#cbd2d9', '#eef2f7'
ss = getSampleStyleSheet()
T = ParagraphStyle('t', fontName='Sans-B', fontSize=17, leading=21, textColor=INK, spaceAfter=4)
H = ParagraphStyle('h', fontName='Sans-B', fontSize=12.5, leading=15, textColor=ACC, spaceBefore=2, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Sans-B', fontSize=9.5, leading=12, textColor=INK, spaceBefore=6, spaceAfter=2)
B = ParagraphStyle('b', fontName='Sans', fontSize=8.6, leading=11.6, textColor=INK, spaceAfter=3)
SM = ParagraphStyle('sm', parent=B, fontSize=8, leading=10.5, textColor=MUTED)
BL = ParagraphStyle('bl', parent=B, leftIndent=10, bulletIndent=2)
CODE = ParagraphStyle('code', fontName='Mono', fontSize=6.6, leading=8.2, textColor=INK, backColor=SOFT,
                      borderPadding=3, spaceBefore=2, spaceAfter=5)
CELL = ParagraphStyle('cell', fontName='Sans', fontSize=7.8, leading=10, textColor=INK)
CELLB = ParagraphStyle('cellb', parent=CELL, fontName='Sans-B')

STRAT = {"silent_highrisk_direct": "High-risk gain in the tool's own code, description unchanged",
         "silent_highrisk_via_helper": "High-risk gain through a helper function, description unchanged",
         "other_tool_gain": "Other capability gain", "silent_server_gain": "Whole server gained a capability; nothing visible changed",
         "suspicious_desc": "Description gained instruction-like text"}
CAP = {"shell": "run shell commands / programs", "env_secrets": "read environment variables or secrets",
       "fs_write": "write or delete files", "fs_read": "read local files", "network": "make network requests",
       "dynamic_code": "run dynamically generated code"}


def pre(text):
    """Monospace block; shrink the font so the widest line fits (down to 4.6 pt), wrap only beyond that."""
    width_pt = 172 * mm - 8
    longest = max((len(l) for l in text.split('\n')), default=1)
    size = max(4.6, min(6.6, width_pt / (0.602 * max(longest, 1))))
    st = ParagraphStyle('c%.1f' % size, parent=CODE, fontSize=size, leading=size * 1.24)
    return Preformatted(wrap(text, int(width_pt / (0.602 * size))), st)


def wrap(text, width=118):
    out = []
    for line in text.split('\n'):
        while len(line) > width:
            out.append(line[:width]); line = '    ' + line[width:]
        out.append(line)
    return '\n'.join(out)


def inline(s):
    s = escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<font name="Mono" size="7.6">\1</font>', s)
    s = re.sub(r'(https?://[^\s<)]+)', r'<link href="\1" color="#1d4e89">\1</link>', s)
    return s


def md(text):
    """Small markdown renderer: headings, code fences, tables (kept monospace), bullets, paragraphs."""
    flow, buf, code, inside = [], [], [], False
    def flush():
        if buf:
            flow.append(Paragraph(inline(' '.join(buf)), B)); buf.clear()
    for line in text.split('\n'):
        if line.strip().startswith('```'):
            if inside:
                flow.append(pre('\n'.join(code))); code.clear(); inside = False
            else:
                flush(); inside = True
            continue
        if inside:
            code.append(line); continue
        if line.startswith('|'):
            flush(); code.append(line); continue
        elif code:
            flow.append(pre('\n'.join(code))); code.clear()
        if line.startswith('# '):
            continue  # item title is printed separately
        if line.startswith('#'):
            flush(); flow.append(Paragraph(inline(line.lstrip('#').strip()), H2)); continue
        if re.match(r'^\s*[-*] ', line):
            flush(); flow.append(Paragraph(inline(re.sub(r'^\s*[-*] ', '', line)), BL, bulletText='•')); continue
        if not line.strip():
            flush(); continue
        buf.append(line.strip())
    flush()
    if code:
        flow.append(pre('\n'.join(code)))
    return flow


def main():
    s = open(f'{R}/validation/label.html').read()
    data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', s, re.S)
                      .group(1).replace('<\\/', '</'))
    ev = {f"e-{e['id']}": e for e in data['events']}
    items = list(csv.DictReader(open(f'{R}/maps/items.csv')))[:N]

    story = [Paragraph('MCP Drift: Labelling Packet', T),
             Paragraph(f'Items 1–{N}, in the same order as the labelling page. Blind round: facts only.', SM),
             Spacer(1, 6),
             Paragraph('How to use this packet', H),
             Paragraph('For each item: read <b>What this server does</b> and the <b>tool description</b>, check the '
                       '<b>added lines</b>, open the <b>GitHub diff</b> if needed, then read the <b>code map</b> '
                       '(call path from the tool to the flagged code). Decide, then record your label on the labelling '
                       'page. Read the item\'s observations file only <b>after</b> labelling. No AI chat while labelling.', B),
             Paragraph('Labels', H2)]
    lab = [['Extraction error', 'The capability was not newly reachable from this tool: code only moved, the wrong function '
            'was matched, it sits in tests/build/CLI code, or it already existed in the old version.'],
           ['Benign', 'Newly reachable, and routine for what the tool is for (its own config, cache, API key, service).'],
           ['Security relevant', 'Newly reachable, and a user who approved the old version would plausibly want to know '
            '(commands from AI input, other secrets, writes outside its own area, new outside destinations, '
            'description that hides or contradicts behaviour).'],
           ['Unsure', 'Cannot tell in about 3 minutes. Add a note.']]
    t = Table([[Paragraph(a, CELLB), Paragraph(b, CELL)] for a, b in lab], colWidths=[32 * mm, 140 * mm])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor(LINE)), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    story += [t, Spacer(1, 6), Paragraph('Two questions per item', H2),
              Paragraph('1. Is the flagged capability <b>really new</b> and <b>really reachable from this tool</b>? '
                        'If no → extraction error.<br/>2. If yes: is it <b>expected</b> given the tool\'s description '
                        'and the server\'s purpose? Yes → benign; no → security relevant.', B),
              Paragraph('Index', H2)]
    idx = [[Paragraph(x, CELLB) for x in ('#', 'Item', 'Repository', 'Tool', 'Flagged')]]
    for r in items:
        idx.append([Paragraph(r['page_position'], CELL), Paragraph(r['item'], CELL), Paragraph(escape(r['repo']), CELL),
                    Paragraph(escape(r['tool']), CELL), Paragraph(escape(r['flagged_capability']), CELL)])
    t = Table(idx, colWidths=[8 * mm, 13 * mm, 70 * mm, 50 * mm, 31 * mm], repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor(LINE)),
                           ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(SOFT)),
                           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]))
    story += [t]

    for r in items:
        e = ev.get(r['item'], {})
        story.append(PageBreak())
        story.append(Paragraph(f"#{r['page_position']} · {r['item']} · {escape(r['repo'])}", H))
        isdesc = r['category'] == 'suspicious_desc'
        what = ("The tool's <b>description</b> gained instruction-like text (markers: " + escape(r['flagged_capability']) + ")."
                if isdesc else f"Flagged: the {'tool <b>' + escape(r['tool']) + '</b>' if r['tool'] != '(whole server)' else '<b>whole server</b>'} "
                f"seems to have gained the ability to <b>{CAP.get(r['flagged_capability'], r['flagged_capability'])}</b>.")
        via = r['found_via']
        where = ('' if isdesc or not via else
                 ("Found in the tool's own handler." if via == 'self' else f"Found through helper <font name='Mono'>{escape(via)}</font>."))
        about = (e.get('about') or {}).get('d') or '(no GitHub description)'
        rows = [['Category', STRAT.get(r['category'], r['category'])],
                ['What the server does', about],
                ['Flag', what + (' ' + where if where else '')],
                ['Versions', f"{r['old_version']} → {r['new_version']}"],
                ['Code change (diff)', f'<link href="{r["compare_url"]}" color="#1d4e89">{escape(r["compare_url"])}</link>'],
                ['Repository', f'<link href="https://github.com/{r["repo"]}" color="#1d4e89">https://github.com/{escape(r["repo"])}</link>'],
                ['Code map (online)', f'<link href="https://github.com/CosmicMicra/mcp-drift/blob/main/maps/{r["item"]}.md" color="#1d4e89">maps/{r["item"]}.md</link>']]
        t = Table([[Paragraph(a, CELLB), Paragraph(b if a in ('Flag', 'Code change (diff)', 'Repository', 'Code map (online)') else escape(b), CELL)]
                   for a, b in rows], colWidths=[34 * mm, 138 * mm])
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor(LINE)), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(SOFT)),
                               ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]))
        story += [t, Spacer(1, 4)]
        evd = e.get('ev') or {}
        if not isdesc and evd.get('n_add') is not None:
            story.append(Paragraph('Lines added in this version that match the flag (server code, tests excluded)', H2))
            if evd['n_add']:
                txt = '\n'.join(f"{f}\n  + {l}" for f, l in evd['add'])
                if evd['n_add'] > len(evd['add']):
                    txt += f"\n… and {evd['n_add'] - len(evd['add'])} more"
                story.append(pre(txt))
                if evd.get('n_rem'):
                    story.append(Paragraph(f"{evd['n_rem']} similar line(s) were <b>removed</b> in the same change "
                                           "(possible move or refactor).", SM))
            else:
                story.append(Paragraph('<b>No matching lines were added in server code.</b> Often a sign of an extraction error.', SM))
        if isdesc:
            story.append(Paragraph('Old description', H2)); story.append(pre(e.get('old') or '(not recorded)'))
            story.append(Paragraph('New description', H2)); story.append(pre(e.get('new') or '(not recorded)'))
        elif e.get('new'):
            story.append(Paragraph('Tool description (unchanged)', H2)); story.append(pre(e['new']))
        story.append(Paragraph('Code map (facts only)', H))
        try:
            story += md(open(f"{R}/maps/{r['item']}.md").read())
        except FileNotFoundError:
            story.append(Paragraph('(no map file)', SM))
        box = Table([[Paragraph('<b>Your label:</b>  ☐ Extraction error   ☐ Benign   ☐ Security relevant   ☐ Unsure', CELL)],
                     [Paragraph('<b>Notes:</b>', CELL)], [Paragraph(' ', CELL)]], colWidths=[172 * mm], rowHeights=[None, None, 14 * mm])
        box.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor(ACC)), ('TOPPADDING', (0, 0), (-1, -1), 4)]))
        story += [Spacer(1, 6), KeepTogether(box)]

    def footer(c, d):
        c.saveState(); c.setFont('Sans', 7); c.setFillColor(colors.HexColor(MUTED))
        c.drawString(18 * mm, 10 * mm, 'MCP drift labelling packet · blind round · observations excluded')
        c.drawRightString(letter[0] - 18 * mm, 10 * mm, f'Page {d.page}'); c.restoreState()
    SimpleDocTemplate(OUT, pagesize=letter, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm,
                      bottomMargin=16 * mm, title=f'MCP Drift Labelling Packet 1-{N}').build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


main()
