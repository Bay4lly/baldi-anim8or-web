const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(__dirname+'/../app.js','utf8');
const a=src.indexOf('function shortestAngleDelta');
const b=src.indexOf('function valueAt',a);
if(a<0||b<0) throw new Error('Interpolation engine block not found');
const ctx={console,Math,clamp:(v,a,b)=>Math.max(a,Math.min(b,v))};
vm.createContext(ctx);vm.runInContext(src.slice(a,b),ctx);
const e=ctx.evalTrack;
function near(actual,expected,eps=1e-7,msg=''){assert.ok(Math.abs(actual-expected)<=eps,`${msg} got ${actual}, expected ${expected}`);}
// Linear: tam düz.
near(e([{f:0,v:0,type:'linear'},{f:10,v:10,type:'linear'}],5,false),5,1e-9,'linear midpoint');
// Step: hedef key'e kadar hiçbir geçiş yok.
near(e([{f:0,v:0,type:'step'},{f:10,v:10,type:'linear'}],5,false),0,1e-9,'step hold');
near(e([{f:0,v:0,type:'step'},{f:10,v:10,type:'linear'}],9.999,false),0,1e-9,'step pre-target');
near(e([{f:0,v:0,type:'step'},{f:10,v:10,type:'linear'}],10,false),10,1e-9,'step exact target');
// Rotation shortest path.
near(e([{f:0,v:170,type:'linear'},{f:10,v:-170,type:'linear'}],5,true),180,1e-9,'shortest angle');
// Smooth C1 continuity, ordinary keys must NOT hard-stop.
const smooth=[{f:0,v:0,type:'smooth'},{f:10,v:10,type:'smooth'},{f:20,v:15,type:'smooth'},{f:30,v:30,type:'smooth'}];
const h=.001;
const dl=(e(smooth,10,false)-e(smooth,10-h,false))/h;
const dr=(e(smooth,10+h,false)-e(smooth,10,false))/h;
assert.ok(Math.abs(dl-dr)<0.01,`smooth tangent discontinuity: left=${dl}, right=${dr}`);
assert.ok(Math.abs(dl)>0.1,`smooth should not hard-stop at ordinary middle key: derivative=${dl}`);
// Asıl V9 regression testi: key aralıkları eşit değil ama hareket sabit hızlıysa Smooth hiçbir keyde yavaşlamamalı.
const constantSpeed=[
  {f:0,v:0,type:'smooth'},
  {f:5,v:10,type:'smooth'},
  {f:20,v:40,type:'smooth'},
  {f:30,v:60,type:'smooth'}
];
for(const f of [1,2.5,4.9,5.1,8,12.5,19.9,20.1,25,29]) near(e(constantSpeed,f,false),2*f,1e-7,`constant-speed smooth F${f}`);
const l=(e(constantSpeed,5,false)-e(constantSpeed,5-h,false))/h;
const r=(e(constantSpeed,5+h,false)-e(constantSpeed,5,false))/h;
near(l,2,1e-3,'constant-speed left tangent');near(r,2,1e-3,'constant-speed right tangent');
// Uçlarda tangent zero'ya düşmemeli.
const firstSlope=(e(constantSpeed,h,false)-e(constantSpeed,0,false))/h;
const lastSlope=(e(constantSpeed,30,false)-e(constantSpeed,30-h,false))/h;
near(firstSlope,2,1e-3,'smooth start slope');near(lastSlope,2,1e-3,'smooth end slope');
console.log('Interpolation V9 tests passed', {linear:5,step:0,angle:180,tangentAt5:[l,r],start:firstSlope,end:lastSlope});
