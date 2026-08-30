#!/usr/bin/env python3
import json, pathlib, sys
root=pathlib.Path(__file__).resolve().parents[1]
s=(root/'model-data.js').read_text(encoding='utf-8')
prefix='window.BALDI_MODEL='
assert s.startswith(prefix) and s.rstrip().endswith(';')
model=json.loads(s[len(prefix):].strip()[:-1])
assert len(model['parts'])==41, len(model['parts'])
for name,p in model['parts'].items():
    for mesh in p['meshes']:
        nv=len(mesh['p'])//3
        assert len(mesh['p'])%3==0 and len(mesh['n'])==len(mesh['p'])
        for g in mesh['g']:
            assert len(g['i'])%3==0
            if g['i']:
                assert min(g['i'])>=0 and max(g['i'])<nv, (name,max(g['i']),nv)
# Regression: old fan/cage parser produced a triangular mouth shard down to ~156.41.
# Correct Anim8or subdivision/triangulation keeps Mouth2 above 158 in bind pose.
assert model['parts']['Mouth2']['bbox'][0][1] > 158.0, model['parts']['Mouth2']['bbox']
assert model['compiler']['mode']=='anim8or-figure-bind-v5'
print('Model tests passed:', len(model['parts']), 'parts; Mouth2 minY=', model['parts']['Mouth2']['bbox'][0][1])
