import json,sys
for l in open(sys.argv[1]):
    e=json.loads(l); m=e.get('message') or {}; cs=m.get('content') if isinstance(m.get('content'),list) else []
    for b in cs:
        if b.get('type')=='tool_use':
            i=b['input']; print('TOOL',b['name'],(i.get('command') or i.get('skill') or json.dumps(i))[:300].replace('\n',' '))
        elif b.get('type')=='tool_result':
            c=b.get('content'); c=c if isinstance(c,str) else json.dumps(c)
            print('   ->',c[:250].replace('\n',' | '))
    if e.get('type')=='result': print('RESULT',(e.get('result') or '')[:900])
