from difflib import SequenceMatcher
from .core import is_target, normalized

def candidate_packets(before,after,limit=4):
    """Search all target sections, including moved text; retain split/merge candidates."""
    old=[b for b in before if is_target(b)];new=[b for b in after if is_target(b)]
    oldtexts={normalized(b['text']) for b in old};newtexts={normalized(b['text']) for b in new}
    changed_old=[b for b in old if normalized(b['text']) not in newtexts]
    changed_new=[b for b in new if normalized(b['text']) not in oldtexts]
    def similarity(a,b):
        value=SequenceMatcher(None,a['normalized'],b['normalized'],autojunk=False).ratio()
        if a['section'].split(' > ')[-1]==b['section'].split(' > ')[-1]:value+=.12
        return value
    def with_context(b):return {k:b[k] for k in ['id','reportId','section','text','contextBefore','contextAfter']}
    packets=[];seen=set()
    for oldblock in changed_old:
        candidates=sorted(changed_new,key=lambda n:similarity(oldblock,n),reverse=True)[:limit]
        # Adjacent old blocks allow one-to-many / many-to-one alignment.
        neighbors=[b for b in changed_old if abs(b['order']-oldblock['order'])<=2 and b['section']==oldblock['section']]
        packets.append(dict(before=[with_context(b) for b in neighbors],after=[with_context(b) for b in candidates]))
        seen.update(b['id'] for b in candidates)
    for b in changed_new:
        if b['id'] not in seen:packets.append(dict(before=[],after=[with_context(b)]))
    return packets
