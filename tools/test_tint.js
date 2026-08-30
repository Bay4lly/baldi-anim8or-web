const fs=require('fs'),assert=require('assert');
const src=fs.readFileSync(__dirname+'/../app.js','utf8');
assert.ok(src.includes('vec3 colorized=uTint*shade;c=mix(c,colorized,uTintMix)'), 'shader colorize filter missing');
assert.ok(src.includes("if(id==='partTint'&&(ap.mix??0)<0.01){ap.mix=.8"), 'tint auto-enable missing');
function colorize(c,tint,mix){const shade=Math.max(...c),col=tint.map(v=>v*shade);return c.map((v,i)=>v+(col[i]-v)*mix);}
const out=colorize([0.05,0.9,0.08],[1,0,0],0.8);
assert.ok(out[0]>0.7 && out[1]<0.25, 'red filter should visibly recolor a green surface');
console.log('Tint tests passed',out);
