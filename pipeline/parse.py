from defusedxml import ElementTree as ET
from .core import digest, normalized
from .dart import xml_members

def tag(el):return el.tag.rsplit('}',1)[-1].upper()
def text(el):return ''.join(el.itertext()).strip()

def table_matrix(table):
    rows=[];occupied={};rownum=0
    def walk(node):
        for child in node:
            if tag(child)=='TABLE':continue
            if tag(child)=='TR':yield child
            else:yield from walk(child)
    for tr in walk(table):
        row=[];col=0
        for cell in tr:
            if tag(cell) not in {'TD','TH','TE','TU'}:continue
            while (rownum,col) in occupied:
                row.append(occupied[(rownum,col)]);col+=1
            value=text(cell)
            cols=min(max(int(cell.attrib.get('COLSPAN',cell.attrib.get('colspan',1))),1),100)
            spans=min(max(int(cell.attrib.get('ROWSPAN',cell.attrib.get('rowspan',1))),1),100)
            for dr in range(spans):
                for dc in range(cols):occupied[(rownum+dr,col+dc)]=value
            for dc in range(cols):row.append(value);col+=1
        while (rownum,col) in occupied:row.append(occupied[(rownum,col)]);col+=1
        if row:rows.append(row)
        rownum+=1
    width=max(map(len,rows),default=0)
    return [r+['']*(width-len(r)) for r in rows]

def parse_report(raw,report):
    files=[]
    for filename,xml in xml_members(raw):
        root=ET.fromstring(xml)
        # Annual report main document must contain both business and financial sections.
        titles=[text(e) for e in root.iter() if tag(e) in {'TITLE','SUBTITLE'}]
        if any('사업의 내용' in t for t in titles) and any('재무에 관한 사항' in t for t in titles):files.append((filename,root))
    if len(files)!=1:raise ValueError('사업보고서 본문 XML을 유일하게 식별하지 못했습니다. 원본을 확인하세요.')
    filename,root=files[0];blocks=[];headings={};last_caption=''
    def visit(el,depth=0):
        nonlocal last_caption
        name=tag(el)
        if name in {'TITLE','SUBTITLE'}:
            value=text(el)
            if value:
                headings[depth]=value
                for key in list(headings):
                    if key>depth:del headings[key]
                last_caption=value
            return
        if name=='TABLE':
            rows=table_matrix(el)
            if rows:
                value='\n'.join(' | '.join(r) for r in rows)
                add('table',value,dict(headers=rows[0],rows=rows[1:],unit=last_caption if '단위' in last_caption else '단위: 원문 표와 주변 문맥 확인'))
            return
        if name=='P':
            value=text(el)
            if value:
                if '단위' in value:last_caption=value
                add('paragraph',value,{})
            return
        for child in el:visit(child,depth+1)
    def add(kind,value,extra):
        order=len(blocks);section=' > '.join(headings[k] for k in sorted(headings))
        ident=digest(dict(file=filename,order=order,text=value))[:16]
        blocks.append(dict(id=report['id']+'-'+ident,reportId=report['id'],kind=kind,section=section,order=order,text=value,normalized=normalized(value),contextBefore='',contextAfter='',**extra))
    visit(root)
    for i,b in enumerate(blocks):
        if i and blocks[i-1]['section']==b['section']:b['contextBefore']=blocks[i-1]['text'][-1500:]
        if i+1<len(blocks) and blocks[i+1]['section']==b['section']:b['contextAfter']=blocks[i+1]['text'][:1500]
    if not blocks:raise ValueError('원문에서 문단·표를 추출하지 못했습니다.')
    return blocks
