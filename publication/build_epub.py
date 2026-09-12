#!/usr/bin/env python3
"""Build the intermediate manuscript as EPUB 3; no network or account access."""
from pathlib import Path
import datetime
import html
import re
import zipfile
import xml.etree.ElementTree as ET
import markdown

ROOT=Path(__file__).resolve().parent
NS='http://www.w3.org/1999/xhtml'
STYLE='''body { font-family: serif; line-height: 1.5; margin: 5%; }
h1,h2,h3 { font-family: sans-serif; line-height: 1.2; }
pre { white-space: pre-wrap; font-size: .8em; background: #eee; padding: .7em; }
code { font-family: monospace; } table { border-collapse: collapse; font-size: .8em; }
th,td { border: 1px solid #aaa; padding: .25em; } img { max-width: 100%; }'''

def document(title,body):
    # Markdown's XHTML output uses only XML-compatible empty tags. Convert
    # remaining HTML named entities, retaining XML's five built-in entities.
    body=re.sub(r'&([A-Za-z][A-Za-z0-9]+);',lambda m:m.group(0) if m[1] in ['amp','lt','gt','quot','apos'] else ''.join('&#%d;'%ord(c) for c in html.unescape(m[0])),body)
    result=f'<?xml version="1.0" encoding="utf-8"?><html xmlns="{NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en"><head><title>{html.escape(title)}</title><link rel="stylesheet" href="style.css"/></head><body>{body}</body></html>'
    ET.fromstring(result)
    return result

def build():
    files=sorted((ROOT/'ebook-intermediate').glob('*.md'),key=lambda p:(not p.name.startswith('chapter'),p.name))
    files=[p for p in files if p.name!='README.md']
    assert len(files)==20
    parts=[]
    for p in files:
        source=p.read_text(); title=source.splitlines()[0].lstrip('# ')
        body=markdown.markdown(source,extensions=['fenced_code','tables'],output_format='xhtml')
        parts.append((p.stem,title,document(title,body)))
    nav='<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>'+''.join(f'<li><a href="{name}.xhtml">{html.escape(title)}</a></li>' for name,title,_ in parts)+'</ol></nav>'
    entries={f'EPUB/{name}.xhtml':body for name,_,body in parts}
    entries['EPUB/nav.xhtml']=document('Contents',nav)
    entries['EPUB/cover.xhtml']=document('The Headless Studio','<h1>The Headless Studio</h1><p>Clint Johnson · Intermediate edition</p><img src="cover.jpg" alt="The Headless Studio book cover"/>')
    manifest='<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="coverpage" href="cover.xhtml" media-type="application/xhtml+xml"/><item id="cover" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/><item id="css" href="style.css" media-type="text/css"/>'
    manifest+=''.join(f'<item id="{name}" href="{name}.xhtml" media-type="application/xhtml+xml"/>' for name,_,_ in parts)
    spine='<itemref idref="coverpage"/><itemref idref="nav"/>'+''.join(f'<itemref idref="{name}"/>' for name,_,_ in parts)
    modified=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    opf=f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">urn:headless-studio:intermediate</dc:identifier><dc:title>The Headless Studio</dc:title><dc:creator>Clint Johnson</dc:creator><dc:language>en</dc:language><dc:description>A practical guide to music production with Python.</dc:description><meta property="dcterms:modified">{modified}</meta></metadata><manifest>{manifest}</manifest><spine>{spine}</spine></package>'''
    ET.fromstring(opf)
    out=ROOT/'downloads/the-headless-studio.epub';out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml','<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr('EPUB/package.opf',opf);z.writestr('EPUB/style.css',STYLE)
        z.write(ROOT/'images/book-cover.jpg','EPUB/cover.jpg')
        for name,body in entries.items():z.writestr(name,body)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert z.infolist()[0].filename=='mimetype' and z.infolist()[0].compress_type==0
        for name in z.namelist():
            if name.endswith(('.xhtml','.opf','.xml')):ET.fromstring(z.read(name))
        for name in entries:
            for element in ET.fromstring(z.read(name)).iter():
                link=element.attrib.get('href',element.attrib.get('src',''))
                if link and not re.match(r'[a-z]+:',link) and not link.startswith('#'):
                    assert 'EPUB/'+link.split('#')[0] in z.namelist(),(name,link)
    print(f'Built and validated {out}: {len(parts)} chapters/appendices')
if __name__=='__main__':build()
