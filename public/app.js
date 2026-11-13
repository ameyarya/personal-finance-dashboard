/* Personal Finance Dashboard: front end. No build step, no dependencies.
   State lives in S, every page is rendered from it, and the server beside this file keeps the data. */
(function(){
'use strict';
const CATS=['Housing','Groceries','Utilities','Transport','Dining','Shopping','Health','Kids','Fun','Savings','Other','Transfer'];
const BUDGET_CATS=CATS.filter(c=>c!=='Transfer');
const NEEDS=['Housing','Groceries','Utilities','Transport','Health','Kids'];
const CATMETA={Housing:['home','c1'],Groceries:['bag','c2'],Utilities:['bolt','c3'],Transport:['bus','c4'],Dining:['cup','c5'],Shopping:['tag','c6'],Health:['heart','c6'],Kids:['kid','c4'],Fun:['star','c3'],Savings:['coins','c1'],Other:['dots','c0'],Transfer:['swap','c0'],Income:['down','c2']};
const ICONS={grid:'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',swap:'M7 7h13M16 3l4 4-4 4M17 17H4M8 13l-4 4 4 4',cal:'M5 5h14v15H5zM5 10h14M9 3v4M15 3v4',
 pie:'M12 3a9 9 0 1 0 9 9h-9zM15 3.5A9 9 0 0 1 20.5 9H15z',jar:'M7 8h10l1 12H6zM9 4h6v4H9z',users:'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5a6 6 0 0 1 3.5 5.5',
 sliders:'M4 7h10M18 7h2M4 17h2M10 17h10M16 5v4M8 15v4',home:'M4 11l8-7 8 7M6 10v10h12V10',bag:'M6 8h12l-1 12H7zM9 8a3 3 0 0 1 6 0',bolt:'M13 3L5 14h6l-1 7 8-11h-6z',
 bus:'M6 4h12v13H6zM6 12h12M8 20v-3M16 20v-3',cup:'M5 8h11v5a5.5 5.5 0 0 1-11 0zM16 9h2a2 2 0 0 1 0 5h-2M8 3v2M12 3v2',tag:'M4 4h8l8 8-8 8-8-8zM8.5 8.5h.01',
 heart:'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z',kid:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8.5 14a4 4 0 0 0 7 0M9 9.5h.01M15 9.5h.01',
 star:'M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-3-5.4 3 1.1-6L3.2 9.4l6.1-.8z',coins:'M12 5c4 0 7 1.3 7 3s-3 3-7 3-7-1.3-7-3 3-3 7-3zM5 8v4c0 1.7 3 3 7 3s7-1.3 7-3V8M5 12v4c0 1.7 3 3 7 3s7-1.3 7-3v-4',
 dots:'M6 12h.01M12 12h.01M18 12h.01',down:'M12 4v14M6 12l6 6 6-6',spark:'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18',info:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5M12 8h.01',
 chart:'M5 20V10M12 20V4M19 20v-7',bank:'M4 10h16M6 10v8M10 10v8M14 10v8M18 10v8M3 20h18M12 3l9 5H3z',
 sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19',moon:'M20 14A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 10z',auto:'M12 3a9 9 0 1 0 0 18zM12 3a9 9 0 0 1 0 18',
 upload:'M12 16V4M7 9l5-5 5 5M5 20h14',download:'M12 4v12M7 11l5 5 5-5M5 20h14'};
const ic=(n,col)=>'<svg class="ic" viewBox="0 0 24 24"'+(col?' style="color:var(--'+col+')"':'')+' aria-hidden="true"><path d="'+(ICONS[n]||ICONS.dots)+'"/></svg>';
const catIco=(c,col)=>{const m=CATMETA[c]||CATMETA.Other;return '<span class="ico">'+ic(m[0],col||m[1])+'</span>'};
const VIEWS=[['overview','Overview','grid'],['payments','Payments','swap'],['bills','Bills','cal'],['budgets','Budgets','pie'],['pots','Pots','jar'],['insights','Insights','chart'],['household','Household','users'],['accounts','Accounts','bank']];
const LOCALE={USD:'en-US',EUR:'en-IE',GBP:'en-GB',CAD:'en-CA',AUD:'en-AU',INR:'en-IN',SGD:'en-SG',AED:'en-AE',JPY:'ja-JP',MXN:'es-MX'};
const DEF={household:'Our household',currency:'USD',opening:0,members:['You','Partner']};
const pad=n=>String(n).padStart(2,'0');
const iso=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());
const NOW=new Date(), TODAY=iso(NOW), YM=TODAY.slice(0,7);
const hashView=()=>{const h=location.hash.slice(1);return VIEWS.some(v=>v[0]===h)?h:'overview'};
const S={settings:null,txRaw:[],tx:[],budgets:{},pots:[],rec:[],accounts:[],rules:[],bank:{},ready:false,db:null,month:YM,view:hashView(),span:6,noteIdx:0,note:'',confirmClear:false,confirmDisc:false,q:'',fcat:'',busy:'',anim:'page'};
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cfg=()=>Object.assign({},DEF,S.settings||{});
const daysIn=m=>new Date(+m.slice(0,4),+m.slice(5,7),0).getDate();
const shift=(m,n)=>{const d=new Date(+m.slice(0,4),+m.slice(5,7)-1+n,1);return d.getFullYear()+'-'+pad(d.getMonth()+1)};
const mName=(m,o)=>new Date(+m.slice(0,4),+m.slice(5,7)-1,1).toLocaleDateString('en-US',o||{month:'long',year:'numeric'});
const mLong=m=>mName(m,{month:'long'}), mShort=m=>mName(m,{month:'short'});
const ord=n=>n+(n%100>10&&n%100<14?'th':['th','st','nd','rd'][n%10]||'th');
const dayDiff=(a,b)=>Math.round((new Date(a+'T12:00:00')-new Date(b+'T12:00:00'))/864e5);
const shortDate=d=>new Date(d+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric'});
function fmt(n,compact){const c=cfg().currency;try{return new Intl.NumberFormat(LOCALE[c]||'en-US',{style:'currency',currency:c,maximumFractionDigits:compact?1:0,notation:compact?'compact':'standard'}).format(n)}catch(e){return Math.round(n).toLocaleString()}}
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0);
const flows=a=>a.filter(t=>t.category!=='Transfer');
const outOf=a=>sum(flows(a).filter(t=>t.amount<0),t=>-t.amount);
const incOf=a=>sum(flows(a).filter(t=>t.amount>0),t=>+t.amount);
const plural=(n,one,many)=>n+' '+(n===1?one:(many||one+'s'));

/* ---------- derived figures ---------- */
function derive(){const off=new Set(S.accounts.filter(a=>a.include===false).map(a=>a.id));S.tx=S.txRaw.filter(t=>t.date&&!(t.account&&off.has(t.account)))}
const counted=()=>S.accounts.filter(a=>a.include!==false);
function currentBalance(){const a=counted();return a.length?sum(a,x=>+x.balance||0):(+cfg().opening||0)+sum(S.tx,t=>+t.amount||0)}
function monthData(mo){
  const N=daysIn(mo),cur=mo===YM,last=cur?+TODAY.slice(8):N;
  const mtx=S.tx.filter(t=>t.date.startsWith(mo));
  let bal=currentBalance()-sum(S.tx.filter(t=>t.date>=mo+'-01'),t=>+t.amount||0);
  const byDay=Array(N+2).fill(0); mtx.forEach(t=>{byDay[Math.min(+t.date.slice(8),N)]+=+t.amount||0});
  const actual=[]; for(let d=1;d<=last;d++){bal+=byDay[d];actual.push({d,v:bal})}
  const items=S.rec.map(r=>Object.assign({},r,{due:Math.min(+r.day||1,N),paid:mtx.some(t=>t.recId===r.id)})).sort((a,b)=>a.due-b.due);
  const fc=[],marks=[];
  if(cur&&last<N){let f=bal;fc.push({d:last,v:f});
    for(let d=last+1;d<=N;d++){f+=byDay[d];const due=items.filter(i=>!i.paid&&(i.due===d||(d===last+1&&i.due<=last)));due.forEach(i=>f+=+i.amount);fc.push({d,v:f});due.forEach(i=>marks.push({d,v:f,i}))}}
  const unpaidOut=sum(items.filter(i=>!i.paid&&i.amount<0),i=>-i.amount);
  return {mo,N,last,cur,mtx,actual,fc,marks,items,bal,unpaidOut,inc:incOf(mtx),out:outOf(mtx)};
}
function spendByCat(mtx){const o={};flows(mtx).forEach(t=>{if(t.amount<0){const c=t.category||'Other';o[c]=(o[c]||0)-t.amount}});return o}
function notices(m){
  const n=[],prev=monthData(shift(m.mo,-1)),sp=spendByCat(m.mtx);
  if(m.cur){
    const before=outOf(prev.mtx.filter(t=>+t.date.slice(8)<=m.last));
    if(before>0&&m.out>0){const p=Math.round((m.out-before)/before*100);n.push({i:'swap',t:'Spending is '+(p>=0?'up ':'down ')+Math.abs(p)+'%',b:fmt(m.out)+' so far against '+fmt(before)+' by this day in '+mLong(prev.mo)+'.',v:'payments',a:'See payments'})}
    const due=m.items.filter(i=>!i.paid&&i.amount<0);
    if(due.length)n.push({i:'cal',t:plural(due.length,'bill')+' still to pay',b:fmt(m.unpaidOut)+' goes out before the '+ord(m.N)+'. Next is '+esc(due[0].name)+' on the '+ord(due[0].due)+'.',v:'bills',a:'See bills'});
  }
  Object.keys(S.budgets).forEach(k=>{const l=S.budgets[k].limit;if(l&&sp[k]>l)n.push({i:(CATMETA[k]||CATMETA.Other)[0],t:esc(k)+' is over budget',b:fmt(sp[k])+' spent against a budget of '+fmt(l)+', over by '+fmt(sp[k]-l)+'.',v:'budgets',a:'See budgets'})});
  const pot=S.pots.filter(p=>p.target>0&&p.saved<p.target).sort((a,b)=>b.saved/b.target-a.saved/a.target)[0];
  if(pot)n.push({i:'jar',t:esc(pot.name)+' is '+Math.round(pot.saved/pot.target*100)+'% full',b:fmt(pot.target-pot.saved)+' more to reach '+fmt(pot.target)+'.',v:'pots',a:'See pots'});
  const un=m.mtx.filter(t=>t.amount<0&&(t.category||'Other')==='Other').length;
  if(un>=5)n.push({i:'tag',t:plural(un,'payment')+' with no category',b:'Open a payment to pick a category. Tick the box to remember it for next time.',v:'payments',a:'See payments'});
  return n;
}

/* ---------- motion helpers ---------- */
const REDUCED=window.matchMedia&&matchMedia('(prefers-reduced-motion:reduce)');
function restart(el,cls){if(!el)return;el.classList.remove(cls);void el.offsetWidth;el.classList.add(cls)}
function countUp(root){if(REDUCED&&REDUCED.matches)return;
  root.querySelectorAll('[data-n]').forEach(el=>{const to=+el.dataset.n,t0=performance.now(),D=950;if(!isFinite(to))return;
    const f=t=>{if(!el.isConnected)return;const p=Math.min((t-t0)/D,1),e=1-Math.pow(1-p,4);el.textContent=fmt(to*e);if(p<1)requestAnimationFrame(f)};requestAnimationFrame(f)})}
function placePill(){const p=document.querySelector('.navpill'),b=document.querySelector('#nav button.on');if(!p||!b||!b.offsetWidth)return;
  p.style.width=b.offsetWidth+'px';p.style.height=b.offsetHeight+'px';p.style.transform='translate('+b.offsetLeft+'px,'+b.offsetTop+'px)';
  if(!p.classList.contains('ready'))requestAnimationFrame(()=>requestAnimationFrame(()=>p.classList.add('ready')))}
window.addEventListener('resize',placePill);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(placePill);

/* ---------- rendering ---------- */
let raf=0; function schedule(){if(!raf)raf=requestAnimationFrame(()=>{raf=0;render()})}
const themeNow=()=>{try{return localStorage.getItem('theme')||'auto'}catch(e){return 'auto'}};
function render(){
  derive(); const an=S.anim; S.anim='';
  const c=cfg(),m=monthData(S.month),hr=NOW.getHours();
  $('date').textContent=NOW.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
  $('title').textContent=c.household; $('mlabel').textContent=mName(S.month);
  if(an==='page'){restart($('mlabel'),'swap-in');restart($('greet'),'rise');restart($('lede'),'rise')}
  $('greet').textContent=S.view==='overview'?'Good '+(hr<12?'morning':hr<17?'afternoon':'evening'):VIEWS.find(v=>v[0]===S.view)[1];
  let lede='';
  if(S.ready&&!m.cur)lede='Looking back at '+mName(S.month)+'.';
  else if(S.ready){const pay=m.items.find(i=>!i.paid&&i.amount>0&&i.due>=m.last),nb=m.items.filter(i=>!i.paid&&i.amount<0&&(!pay||i.due<=pay.due)).length;
    lede=(pay?pay.name+' lands '+(pay.due===m.last?'today':'in '+plural(pay.due-m.last,'day'))+'. ':'')+(nb?plural(nb,'bill')+(nb===1?' goes':' go')+' out '+(pay?'before then.':'before the month ends.'):pay?'No bills are due before then.':'Nothing is due for the rest of the month.')}
  $('lede').textContent=lede;
  $('next').disabled=S.month>=YM; $('btn-settings').innerHTML=ic('sliders');
  const th=themeNow();$('btn-theme').innerHTML=ic(th==='light'?'sun':th==='dark'?'moon':'auto');$('btn-theme').title='Theme: '+(th==='auto'?'match this device':th);
  const nv=$('nav');
  if(!nv.querySelector('button'))nv.innerHTML='<i class="navpill" aria-hidden="true"></i>'+VIEWS.map(v=>'<button data-act="view" data-id="'+v[0]+'">'+ic(v[2])+'<span>'+v[1]+'</span></button>').join('');
  nv.querySelectorAll('button').forEach(b=>{const on=b.dataset.id===S.view;b.classList.toggle('on',on);if(on)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
  placePill();
  const cm=m.cur?m:monthData(YM);
  $('safe').innerHTML='<span>Safe to spend</span><b>'+(S.ready?fmt(cm.bal-cm.unpaidOut):'…')+'</b><span>'+(S.ready?fmt(cm.unpaidOut)+' of bills still due · '+plural(cm.N-cm.last,'day')+' left':'Loading')+'</span>';

  const nSample=S.txRaw.filter(t=>t.sample).length+S.pots.filter(p=>p.sample).length+S.rec.filter(r=>r.sample).length;
  const b=$('banner');
  if(S.note){b.hidden=false;b.className='banner';b.innerHTML='<span>'+esc(S.note)+'</span>'}
  else if(nSample){b.hidden=false;b.className='banner';
    b.innerHTML=S.confirmClear?'<span><b>Delete '+nSample+' example entries?</b> Your own entries stay.</span><span class="acts"><button class="btn sm" data-act="clear-no">Keep them</button><button class="btn sm primary" data-act="clear-yes">Delete examples</button></span>'
      :'<span><b>Example data.</b> These figures are made up so you can see how the page works. They are not your accounts.</span><span class="acts"><button class="btn sm" data-act="clear-ask">Clear examples</button></span>'}
  else b.hidden=true;

  const card=(cls,html,id)=>'<section class="card '+cls+'"'+(id?' id="'+id+'"':'')+'>'+html+'</section>';
  let h;
  if(!S.ready)h=card('','<div class="empty">Loading your figures…</div>');
  else if(S.view==='overview')h=card('s7',balanceCard(m),'c-balance')+card('s5',flowCard(),'c-flow')+card('s6',catsCard(m),'c-cats')+card('s6',txCard(m,6),'c-tx')+card('s4',noticedCard(m),'c-noticed')+card('s4',potsCard(),'c-pots')+card('s4',dueCard(m,5),'c-due');
  else if(S.view==='payments')h=card('',txCard(m,0),'c-tx');
  else if(S.view==='bills')h=card('',dueCard(m,0),'c-due');
  else if(S.view==='budgets')h=card('',budgetsCard(m),'c-budgets');
  else if(S.view==='pots')h=card('',potsCard(),'c-pots');
  else if(S.view==='insights')h=card('s6',heatCard(m),'c-heat')+card('s6',splitCard(m),'c-split')+card('s7',trendCard(m),'c-trend')+card('s5',biggestCard(m),'c-biggest');
  else if(S.view==='household')h=card('',houseCard(m,c),'c-house');
  else h=card('s6',accountsCard(),'c-accounts')+card('s6',bankCard(),'c-bank')+card('',dataCard(),'c-data');
  const q=document.activeElement&&document.activeElement.id==='q'?document.activeElement.selectionStart:null;
  const vw=$('view');vw.className=an?'anim anim-'+an:'';vw.innerHTML='<div class="grid">'+h+'</div>';
  if(an)countUp(vw);
  if(q!==null&&$('q')){$('q').focus();try{$('q').setSelectionRange(q,q)}catch(e){}}
  if(S.ready&&S.view==='overview')drawChart(m);
}

function balanceCard(m){
  let tiles,chg='';
  if(m.cur){
    const wk=iso(new Date(NOW.getFullYear(),NOW.getMonth(),NOW.getDate()-6)),yr=TODAY.slice(0,4);
    tiles=[['Today',outOf(S.tx.filter(t=>t.date===TODAY))],['This week',outOf(S.tx.filter(t=>t.date>=wk&&t.date<=TODAY))],['This month',m.out],['This year',outOf(S.tx.filter(t=>t.date.startsWith(yr)))]];
    const pm=shift(YM,-1),cut=pm+'-'+pad(Math.min(m.last,daysIn(pm))),was=currentBalance()-sum(S.tx.filter(t=>t.date>cut),t=>+t.amount||0);
    if(was){const p=Math.round((m.bal-was)/Math.abs(was)*100);chg='<div class="sub" style="margin-top:6px"><span class="pill '+(p>=0?'ok':'warn')+'">'+(p>=0?'↑ ':'↓ ')+Math.abs(p)+'%</span> against a month ago</div>'}
  } else tiles=[['In',m.inc],['Out',m.out],['Kept',m.inc-m.out],['Bills paid',m.items.filter(i=>i.paid&&i.amount<0).length]];
  const end=m.fc.length?m.fc[m.fc.length-1].v:null,n=counted().length;
  return '<div class="head"><div><h2>'+(m.cur?'Joint balance':'Balance at the end of '+mLong(m.mo))+'</h2><small>'+(n?plural(n,'linked account')+(S.bank.lastSync?' · synced '+shortDate(S.bank.lastSync.slice(0,10)):''):m.cur?'Spent, by period':mName(m.mo))+'</small></div></div>'+
   '<div class="balrow"><div><div class="big" id="balance" data-n="'+m.bal+'">'+fmt(m.bal)+'</div>'+chg+'</div><div class="tiles">'+tiles.map(t=>'<div class="tile"><span>'+t[0]+'</span><b'+(t[0]==='Bills paid'?'>'+t[1]:' data-n="'+t[1]+'">'+fmt(t[1]))+'</b></div>').join('')+'</div></div>'+
   '<div id="chart"></div>'+
   '<div class="legend"><span><i class="lg-line"></i>Balance</span>'+(m.fc.length?'<span><i class="lg-dot"></i>Forecast</span><span><i class="lg-pt" style="background:var(--accent)"></i>Payday</span><span><i class="lg-pt" style="background:var(--out)"></i>Bill</span><span class="end">'+mShort(m.mo)+' '+m.N+'<b id="month-end" data-n="'+end+'">'+fmt(end)+'</b></span>':'')+'</div>';
}
function drawChart(m){
  const el=$('chart'); if(!el)return; const W=Math.max(el.clientWidth,260),H=190,pl=52,pr=12,pt=22,pb=22;
  const all=m.actual.concat(m.fc).map(p=>p.v); if(!all.length){el.innerHTML='';return}
  let lo=Math.min.apply(0,all),hi=Math.max.apply(0,all); if(hi-lo<1){hi+=1;lo-=1} const pd=(hi-lo)*.12; lo-=pd;hi+=pd;
  const x=d=>pl+(m.N>1?(d-1)/(m.N-1):0)*(W-pl-pr), y=v=>pt+(hi-v)/(hi-lo)*(H-pt-pb);
  const path=a=>a.map((p,i)=>(i?'L':'M')+x(p.d).toFixed(1)+' '+y(p.v).toFixed(1)).join(' ');
  let s='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Balance through the month"><defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--accent)" stop-opacity=".3"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>';
  for(let i=0;i<3;i++){const v=lo+pd+(hi-lo-2*pd)*i/2,yy=y(v);s+='<line x1="'+pl+'" x2="'+(W-pr)+'" y1="'+yy+'" y2="'+yy+'" stroke="var(--line)" stroke-width="1"/><text class="axis" x="'+(pl-8)+'" y="'+(yy+4)+'" text-anchor="end">'+esc(fmt(v,true))+'</text>'}
  [1,Math.round(m.N/4),Math.round(m.N/2),Math.round(m.N*3/4),m.N].forEach((d,i)=>{s+='<text class="axis" x="'+x(d)+'" y="'+(H-5)+'" text-anchor="'+(i===0?'start':i===4?'end':'middle')+'">'+d+'</text>'});
  const a=m.actual;
  if(m.cur&&a.length){const tx=x(m.last);s+='<line x1="'+tx+'" x2="'+tx+'" y1="'+pt+'" y2="'+(H-pb)+'" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 4"/><text class="axis today" x="'+tx+'" y="12" text-anchor="'+(tx>W-60?'end':'middle')+'">Today</text>'}
  if(a.length){
    s+='<path d="'+path(a)+' L'+x(a[a.length-1].d).toFixed(1)+' '+(H-pb)+' L'+x(a[0].d).toFixed(1)+' '+(H-pb)+' Z" fill="url(#ag)" class="fade"/>';
    s+='<path d="'+path(a)+'" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" pathLength="1" class="draw"/>';}
  if(m.fc.length){s+='<path d="'+path(m.fc)+'" fill="none" stroke="var(--accent)" stroke-width="2" stroke-dasharray="1 6" stroke-linecap="round" class="fade late"/>';
    m.marks.forEach(k=>{s+='<circle cx="'+x(k.d)+'" cy="'+y(k.v)+'" r="4.5" class="pop" fill="'+(k.i.amount>0?'var(--accent)':'var(--out)')+'" stroke="var(--bg)" stroke-width="1.5"><title>'+esc(k.i.name)+' '+esc(fmt(k.i.amount))+' on the '+ord(k.d)+'</title></circle>'})}
  s+='<line class="xl" y1="'+pt+'" y2="'+(H-pb)+'" stroke="var(--muted)" stroke-width="1" opacity="0"/><rect class="xd" width="10" height="10" rx="5" fill="var(--accent)" stroke="var(--bg)" stroke-width="2" opacity="0"/>';
  el.innerHTML=s+'</svg><div class="charttip" hidden></div>';
  const pts=m.actual.map(p=>({p:p,f:0})).concat(m.fc.slice(1).map(p=>({p:p,f:1}))),svg=el.querySelector('svg'),tip=el.querySelector('.charttip'),xl=el.querySelector('.xl'),xd=el.querySelector('.xd');
  const off=()=>{tip.hidden=true;xl.setAttribute('opacity',0);xd.setAttribute('opacity',0)};
  el.onmousemove=e=>{const r=svg.getBoundingClientRect(),px=(e.clientX-r.left)*(W/r.width),d=Math.round(1+(px-pl)/(W-pl-pr)*(m.N-1));
    let best=null;pts.forEach(q=>{if(!best||Math.abs(q.p.d-d)<Math.abs(best.p.d-d))best=q});if(!best||px<pl-10||px>W-pr+10)return off();
    const cx=x(best.p.d),cy=y(best.p.v);xl.setAttribute('x1',cx);xl.setAttribute('x2',cx);xl.setAttribute('opacity',.5);xd.setAttribute('x',cx-5);xd.setAttribute('y',cy-5);xd.setAttribute('opacity',1);
    tip.hidden=false;tip.innerHTML='<small>'+esc(mShort(m.mo))+' '+best.p.d+(best.f?' · forecast':'')+'</small><b>'+esc(fmt(best.p.v))+'</b>';
    const tw=tip.offsetWidth;tip.style.left=Math.min(Math.max(cx*(r.width/W),tw/2),r.width-tw/2)+'px';tip.style.top=Math.max(cy*(r.height/H)-8,0)+'px'};
  el.onmouseleave=off;
}

function flowCard(){
  const ms=[];for(let i=S.span-1;i>=0;i--)ms.push(shift(S.month,-i));
  const d=ms.map(mo=>{const t=S.tx.filter(x=>x.date.startsWith(mo));return{mo,i:incOf(t),o:outOf(t)}});
  const mx=Math.max.apply(0,d.map(x=>Math.max(x.i,x.o)))||1,ti=sum(d,x=>x.i),to=sum(d,x=>x.o);
  return '<div class="head"><div><h2>Money in and out</h2><small>The last '+(S.span===3?'three':S.span===6?'six':'twelve')+' months</small></div><div class="seg" role="group" aria-label="Period">'+[[3,'Quarter'],[6,'6 months'],[12,'Year']].map(o=>'<button data-act="span" data-id="'+o[0]+'"'+(S.span===o[0]?' class="on" aria-pressed="true"':'')+'>'+o[1]+'</button>').join('')+'</div></div>'+
   '<div class="legend"><span><i class="lg-pt" style="background:var(--accent)"></i>In <b style="color:var(--fg)">'+fmt(ti)+'</b></span><span><i class="lg-pt" style="background:var(--c0)"></i>Out <b style="color:var(--fg)">'+fmt(to)+'</b></span><span>Kept <b class="in">'+fmt(ti-to)+'</b></span></div>'+
   '<div class="flow">'+d.map(x=>'<div class="col'+(x.mo===S.month?' sel':'')+'" title="'+esc(mName(x.mo))+': in '+esc(fmt(x.i))+', out '+esc(fmt(x.o))+'"><div class="tubes"><div class="tube i"><i style="height:'+(x.i/mx*100).toFixed(1)+'%"></i></div><div class="tube o"><i style="height:'+(x.o/mx*100).toFixed(1)+'%"></i></div></div><small>'+mShort(x.mo)+'</small></div>').join('')+'</div>'+
   '<div class="sub">A full tube is '+fmt(mx,true)+'.</div>';
}

function catsCard(m){
  const sp=spendByCat(m.mtx),keys=Object.keys(sp).sort((a,b)=>sp[b]-sp[a]),tot=m.out||1,top=keys.slice(0,5),rest=sum(keys.slice(5),k=>sp[k]);
  let h='<div class="head"><div><h2>Where '+mLong(m.mo)+' went</h2><small>'+(m.cur?m.last+' of '+m.N+' days in · ':'')+fmt(m.out)+' spent</small></div><button class="link" data-act="view" data-id="budgets">Budgets</button></div>';
  if(!keys.length)return h+'<div class="empty">Nothing spent in '+mLong(m.mo)+' yet.</div>';
  h+='<div class="stack" aria-hidden="true">'+top.map((k,r)=>'<i style="flex:'+sp[k]+';background:var(--c'+(r+1)+')"></i>').join('')+(rest?'<i style="flex:'+rest+';background:var(--track)"></i>':'')+'</div>';
  h+='<div class="list">'+top.map((k,r)=>{const l=S.budgets[k]&&S.budgets[k].limit;
    return '<div class="row">'+catIco(k,'c'+(r+1))+'<div class="t"><b>'+esc(k)+(l&&sp[k]>l?' <span class="pill bad">Over</span>':'')+'</b></div><div class="pct">'+Math.round(sp[k]/tot*100)+'%</div><div class="amt">'+fmt(sp[k])+'</div></div>'}).join('')+
    (rest?'<div class="row">'+catIco('Other')+'<div class="t"><b>'+plural(keys.length-5,'more category','more categories')+'</b></div><div class="pct">'+Math.round(rest/tot*100)+'%</div><div class="amt">'+fmt(rest)+'</div></div>':'')+'</div>';
  if(m.cur&&m.last<m.N){const fixed=outOf(m.mtx.filter(t=>t.recId)),flex=m.out-fixed,proj=m.out+m.unpaidOut+flex/m.last*(m.N-m.last),prev=monthData(shift(m.mo,-1));
    h+='<div class="hint">'+ic('info','accent')+'<span>At this pace '+mLong(m.mo)+' ends near <b>'+fmt(proj)+'</b>'+(prev.out?'. '+mLong(prev.mo)+' was '+fmt(prev.out):'')+'.</span></div>'}
  return h;
}

function filtered(m){const q=S.q.trim().toLowerCase();
  return m.mtx.filter(t=>(!S.fcat||(t.amount>0&&t.category!=='Transfer'?'Income':t.category||'Other')===S.fcat)&&(!q||((t.desc||'')+' '+(t.category||'')+' '+(t.who||'')).toLowerCase().includes(q)))
    .sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:(a.id<b.id?1:-1))}
function txRows(list,full){
  if(!list.length)return '<div class="empty">'+(S.q||S.fcat?'No payments match.':'No payments recorded for '+mLong(S.month)+'. Use Add payment to enter the first one, or import a statement.')+'</div>';
  const acct={};S.accounts.forEach(a=>acct[a.id]=a.name);
  return '<div class="list">'+list.map(t=>{const dd=dayDiff(TODAY,t.date),when=dd===0?'Today':dd===1?'Yesterday':shortDate(t.date),cat=t.amount>0&&t.category!=='Transfer'?'Income':(t.category||'Other');
    return '<div class="row'+(full?' click" data-act="edit-tx" data-id="'+esc(t.id)+'" tabindex="0" role="button':'')+'">'+catIco(cat)+'<div class="t"><b>'+esc(t.desc||'Payment')+'</b><small>'+when+' · '+esc(cat)+(t.who?' · '+esc(t.who):'')+(full&&t.account&&acct[t.account]?' · '+esc(acct[t.account]):'')+'</small></div><div class="amt '+(t.amount>0?'in':'')+'">'+(t.amount>0?'+':'−')+fmt(Math.abs(t.amount))+'</div><div class="acts">'+(full?'<button class="x" data-act="del-tx" data-id="'+esc(t.id)+'" aria-label="Delete '+esc(t.desc||'payment')+'">×</button>':'')+'</div></div>'}).join('')+'</div>';
}
function txCard(m,limit){
  if(limit){const list=m.mtx.slice().sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:0);
    return '<div class="head"><div><h2>Latest payments</h2><small>Everyone, every account</small></div><button class="link" data-act="view" data-id="payments">See all</button></div>'+txRows(list.slice(0,limit),false)}
  const list=filtered(m);
  return '<div class="head"><div><h2>Payments in '+mLong(m.mo)+'</h2><small id="tx-count">'+plural(list.length,'entry','entries')+' · in '+fmt(incOf(list))+' · out '+fmt(outOf(list))+'</small></div></div>'+
   '<div class="toolbar"><input type="search" id="q" placeholder="Search payments" aria-label="Search payments" value="'+esc(S.q)+'"><select id="fcat" aria-label="Category"><option value="">All categories</option>'+CATS.concat('Income').map(c=>'<option'+(c===S.fcat?' selected':'')+'>'+c+'</option>').join('')+'</select>'+
   '<button class="btn" data-act="import-csv">'+ic('upload')+'Import CSV</button><a class="btn" href="api/export.csv" download="payments.csv">'+ic('download')+'Export</a></div>'+
   '<div id="tx-list">'+txRows(list,true)+'</div>';
}
function refreshTx(){if(!$('tx-list'))return;const m=monthData(S.month),list=filtered(m);$('tx-list').innerHTML=txRows(list,true);$('tx-count').textContent=plural(list.length,'entry','entries')+' · in '+fmt(incOf(list))+' · out '+fmt(outOf(list))}

function noticedCard(m){
  const n=notices(m),title='<h2 style="display:flex;gap:8px;align-items:center">'+ic('spark','accent')+'Noticed</h2>';
  if(!n.length)return '<div class="head">'+title+'</div><div class="empty">Nothing stands out this month.</div>';
  const i=((S.noteIdx%n.length)+n.length)%n.length,x=n[i];
  return '<div class="head"><div>'+title+'<small id="note-pos">'+(i+1)+' of '+n.length+'</small></div>'+(n.length>1?'<div style="display:flex;gap:6px"><button class="btn icon" data-act="note" data-id="-1" aria-label="Previous">‹</button><button class="btn icon" data-act="note" data-id="1" aria-label="Next">›</button></div>':'')+'</div>'+
   '<span class="ico">'+ic(x.i,'accent')+'</span><div class="note"><h3>'+x.t+'</h3><p>'+x.b+'</p></div><div><button class="link" style="padding-left:0" data-act="view" data-id="'+x.v+'">'+x.a+' →</button></div>'+
   '<div class="steps">'+n.map((_,k)=>'<i'+(k===i?' class="on"':'')+'></i>').join('')+'</div>';
}

function potsCard(){
  let h='<div class="head"><div><h2>Savings pots</h2><small>'+fmt(sum(S.pots,p=>+p.saved||0))+' put aside</small></div><button class="btn sm" data-act="add-pot">New pot</button></div>';
  if(!S.pots.length)return h+'<div class="empty">No pots yet. Create one for each thing you are saving towards.</div>';
  return h+'<div>'+S.pots.map(p=>{const r=p.target?Math.min((+p.saved||0)/p.target,1):0;
    return '<div class="cat" data-pot="'+esc(p.id)+'"><div class="l"><b>'+esc(p.name)+' '+(r>=1?'<span class="pill ok">Full</span>':'')+'</b><button class="btn sm" data-act="pot" data-id="'+esc(p.id)+'">Add money</button></div><div class="bar"><i style="width:'+(r*100).toFixed(1)+'%"></i></div><div class="l"><span>'+fmt(+p.saved||0)+' of '+fmt(+p.target||0)+'</span><span>'+Math.round(r*100)+'%</span></div></div>'}).join('')+'</div>';
}

function dueCard(m,limit){
  const all=m.items,list=limit?all.filter(i=>!i.paid).concat(all.filter(i=>i.paid)).slice(0,limit):all;
  let h='<div class="head"><div><h2>'+(limit?'Coming up':'Bills and paydays')+'</h2><small>'+(limit?'Bills and paydays in '+mLong(m.mo):'Repeats every month · '+mLong(m.mo)+' shown')+'</small></div>'+(limit?'<button class="link" data-act="view" data-id="bills">All bills</button>':'<button class="btn sm" data-act="add-rec">Add</button>')+'</div>';
  if(!all.length)return h+'<div class="empty">No regular bills or paydays yet. Add rent, subscriptions and paychecks and they will appear in the forecast.</div>';
  return h+'<div class="list">'+list.map(i=>{const inc=i.amount>0,dd=i.due-m.last,
      st=i.paid?(inc?'received':'paid'):!m.cur?'not recorded':dd<0?'overdue':dd===0?'today':'in '+plural(dd,'day');
    return '<div class="row" data-rec="'+esc(i.id)+'"><div class="day"><b>'+i.due+'</b><small>'+mShort(m.mo)+'</small></div><div class="t"><b>'+esc(i.name)+'</b><small>'+(!i.paid&&m.cur&&dd<0?'<span class="pill bad">Overdue</span>':st)+'</small></div>'+
      (!i.paid&&m.cur?'<div class="amt"><button class="btn sm" data-act="pay" data-id="'+esc(i.id)+'">'+(inc?'Received ':'Pay ')+fmt(Math.abs(i.amount))+'</button></div>':'<div class="amt '+(inc?'in':'')+'">'+(inc?'+':'')+fmt(Math.abs(i.amount))+'</div>')+
      '<div class="acts">'+(!limit?'<button class="x" data-act="del-rec" data-id="'+esc(i.id)+'" aria-label="Remove '+esc(i.name)+'">×</button>':'')+'</div></div>'}).join('')+'</div>';
}

function budgetsCard(m){
  const sp=spendByCat(m.mtx),pace=m.cur?m.last/m.N:1;
  const keys=Array.from(new Set(Object.keys(sp).concat(Object.keys(S.budgets).filter(k=>S.budgets[k].limit)))).sort((a,b)=>(sp[b]||0)-(sp[a]||0));
  const mx=Math.max.apply(0,keys.map(k=>sp[k]||0))||1;
  let h='<div class="head"><div><h2>Budgets for '+mLong(m.mo)+'</h2><small>'+(m.cur?'The marker shows where spending should be on day '+m.last+' of '+m.N:'Final figures')+'</small></div><button class="btn sm" data-act="settings">Edit budgets</button></div>';
  if(!keys.length)return h+'<div class="empty">Nothing spent and no budgets set.</div>';
  return h+'<div>'+keys.map(k=>{const v=sp[k]||0,l=S.budgets[k]&&S.budgets[k].limit,name='<b style="display:flex;gap:10px;align-items:center">'+catIco(k)+esc(k);
    if(!l)return '<div class="cat" data-cat="'+esc(k)+'"><div class="l">'+name+'</b><span>'+fmt(v)+' · no budget</span></div><div class="bar nob"><i style="width:'+(v/mx*100).toFixed(1)+'%"></i></div></div>';
    const r=v/l,over=r>1,fast=!over&&m.cur&&r>pace+.1;
    return '<div class="cat" data-cat="'+esc(k)+'"><div class="l">'+name+' '+(over?'<span class="pill bad">Over</span>':fast?'<span class="pill warn">Ahead of pace</span>':'')+'</b><span>'+fmt(v)+' of '+fmt(l)+'</span></div><div class="bar'+(over?' over':fast?' fast':'')+'"><i style="width:'+Math.min(r*100,100).toFixed(1)+'%"></i>'+(m.cur?'<u style="left:'+(pace*100).toFixed(1)+'%"></u>':'')+'</div></div>'}).join('')+'</div>';
}

function houseCard(m,c){
  const by={},inc={};flows(m.mtx).forEach(t=>{const k=t.who||'Shared';if(t.amount<0)by[k]=(by[k]||0)-t.amount;else inc[k]=(inc[k]||0)+ +t.amount});
  const names=Array.from(new Set(c.members.concat(Object.keys(by),Object.keys(inc)))),mx=Math.max.apply(0,names.map(n=>by[n]||0))||1;
  return '<div class="head"><div><h2>Who spent what</h2><small>'+mName(m.mo)+' · Shared covers payments with no person set</small></div></div><div>'+
   names.map(n=>'<div class="cat"><div class="l"><b style="display:flex;gap:10px;align-items:center"><span class="av">'+esc(n.split(/\s+/).map(s=>s[0]).join('').slice(0,2).toUpperCase())+'</span>'+esc(n)+'</b><span>'+(inc[n]?'brought in '+fmt(inc[n])+' · ':'')+'spent '+fmt(by[n]||0)+'</span></div><div class="bar"><i style="width:'+((by[n]||0)/mx*100).toFixed(1)+'%"></i></div></div>').join('')+'</div>';
}

/* ---------- insights ---------- */
function heatCard(m){
  const by=Array(m.N+1).fill(0);flows(m.mtx).forEach(t=>{if(t.amount<0)by[Math.min(+t.date.slice(8),m.N)]-=t.amount});
  const mx=Math.max.apply(0,by)||1,lead=(new Date(+m.mo.slice(0,4),+m.mo.slice(5,7)-1,1).getDay()+6)%7;
  let cells=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d=>'<small>'+d+'</small>').join('')+Array(lead).fill('<span></span>').join('');
  for(let d=1;d<=m.N;d++)cells+='<div class="'+(m.cur&&d>m.last?'future':'')+'" title="'+esc(mShort(m.mo)+' '+d+': '+fmt(by[d]))+'"><i style="opacity:'+(by[d]/mx*.85).toFixed(2)+'"></i><span>'+d+'</span></div>';
  const top=by.indexOf(Math.max.apply(0,by));
  return '<div class="head"><div><h2>Spending by day</h2><small>'+(by[top]?'Heaviest day was the '+ord(top)+' at '+fmt(by[top]):'Nothing spent yet')+'</small></div></div><div class="heat" id="heat">'+cells+'</div>';
}
function splitCard(m){
  const sp=spendByCat(m.mtx);let needs=0,wants=0,save=0;
  Object.keys(sp).forEach(k=>{if(k==='Savings')save+=sp[k];else if(NEEDS.includes(k))needs+=sp[k];else wants+=sp[k]});
  const base=m.inc||needs+wants+save||1,rows=[['Needs','c1',needs,50,'Housing, groceries, utilities, transport, health, kids'],['Wants','c3',wants,30,'Dining, shopping, fun and everything else'],['Saved','c2',save,20,'Money moved to savings and investments']];
  return '<div class="head"><div><h2>Needs, wants and savings</h2><small>As a share of '+(m.inc?'the '+fmt(m.inc)+' that came in':'what went out')+' · a common guide is 50 / 30 / 20</small></div></div>'+
   '<div class="tri" aria-hidden="true">'+rows.map(r=>'<i style="flex:'+(r[2]||0.001)+';background:var(--'+r[1]+')"></i>').join('')+(m.inc>needs+wants+save?'<i style="flex:'+(m.inc-needs-wants-save)+';background:var(--track)"></i>':'')+'</div>'+
   '<div class="list">'+rows.map(r=>'<div class="row"><span class="ico"><i style="width:12px;height:12px;border-radius:50%;background:var(--'+r[1]+')"></i></span><div class="t"><b>'+r[0]+'</b><small>'+r[4]+'</small></div><div class="pct">'+Math.round(r[2]/base*100)+'% · guide '+r[3]+'%</div><div class="amt">'+fmt(r[2])+'</div></div>').join('')+'</div>';
}
function trendCard(m){
  const months=[];for(let i=5;i>=0;i--)months.push(shift(m.mo,-i));
  const per=months.map(mo=>spendByCat(S.tx.filter(t=>t.date.startsWith(mo)))),cats=Array.from(new Set([].concat.apply([],per.map(Object.keys)))).sort((a,b)=>(per[5][b]||0)-(per[5][a]||0));
  if(!cats.length)return '<div class="head"><h2>Categories over time</h2></div><div class="empty">No spending recorded in the last six months.</div>';
  const active=per.filter(p=>Object.keys(p).length).length||1;
  return '<div class="head"><div><h2>Categories over time</h2><small>'+mLong(m.mo)+' against '+mLong(months[4])+' and the six-month average</small></div></div><div class="tablewrap"><table><thead><tr><th>Category</th><th>'+mShort(m.mo)+'</th><th>'+mShort(months[4])+'</th><th>Average</th><th>Against average</th></tr></thead><tbody>'+
   cats.map(c=>{const now=per[5][c]||0,avg=sum(per,p=>p[c]||0)/active,d=avg?Math.round((now-avg)/avg*100):0;
     return '<tr><td>'+esc(c)+'</td><td>'+fmt(now)+'</td><td>'+fmt(per[4][c]||0)+'</td><td>'+fmt(avg)+'</td><td>'+(avg&&now?'<span class="pill '+(d>10?'warn':'ok')+'">'+(d>=0?'↑ ':'↓ ')+Math.abs(d)+'%</span>':'')+'</td></tr>'}).join('')+'</tbody></table></div>';
}
function biggestCard(m){
  const list=flows(m.mtx).filter(t=>t.amount<0).sort((a,b)=>a.amount-b.amount).slice(0,6);
  return '<div class="head"><div><h2>Biggest payments</h2><small>'+mName(m.mo)+'</small></div></div>'+(list.length?txRows(list,false):'<div class="empty">Nothing spent yet.</div>');
}

/* ---------- accounts and data ---------- */
function accountsCard(){
  let h='<div class="head"><div><h2>Accounts</h2><small>'+(S.accounts.length?'Ticked accounts make up the joint balance':'None linked')+'</small></div></div>';
  if(!S.accounts.length)return h+'<div class="empty">The balance is worked out from your opening balance (in Settings) plus every payment recorded here. Link a bank to use real account balances instead.</div>';
  return h+'<div class="list">'+S.accounts.map(a=>'<div class="row" data-acct-row="'+esc(a.id)+'"><span class="ico">'+ic('bank')+'</span><div class="t"><b>'+esc(a.name)+'</b><small>'+esc(a.org||'Bank')+' · as of '+shortDate(a.balanceDate||TODAY)+'</small></div><div class="amt">'+fmt(+a.balance||0)+'</div><label class="check"><input type="checkbox" data-acct="'+esc(a.id)+'"'+(a.include!==false?' checked':'')+' aria-label="Count '+esc(a.name)+' in the joint balance">Count</label></div>').join('')+'</div>';
}
function bankCard(){
  const b=S.bank||{},errs=(b.errors||[]).map(e=>'<div class="err">'+esc(e)+'</div>').join('');
  if(b.connected)return '<div class="head"><div><h2>Bank connection</h2><small>'+(b.lastSync?'Last synced '+new Date(b.lastSync).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'Connected')+' · refreshes about once a day</small></div><span class="pill ok">Connected</span></div>'+errs+
    '<div class="toolbar"><button class="btn primary" data-act="bank-sync"'+(S.busy?' disabled':'')+'>'+(S.busy==='sync'?'Syncing…':'Sync now')+'</button>'+(S.confirmDisc?'<span class="sub">Stop syncing? Payments already fetched stay.</span><button class="btn" data-act="bank-disc-no">Keep</button><button class="btn" data-act="bank-disc-yes">Disconnect</button>':'<button class="btn" data-act="bank-disc-ask">Disconnect</button>')+'</div>';
  return '<div class="head"><div><h2>Bank connection</h2><small>Optional. Fetches balances and payments about once a day.</small></div></div>'+errs+
   '<ol class="steps-list"><li>Create an account at <a href="https://beta-bridge.simplefin.org/" target="_blank" rel="noopener">SimpleFIN Bridge</a> (a paid, read-only service for US and Canadian banks) and link your banks there.</li><li>In its settings, create a new app connection and copy the <b>setup token</b>.</li><li>Paste it here. It is exchanged once for an access key that is kept only on this server, in <code>data/secrets.json</code>.</li></ol>'+
   '<div class="toolbar"><input class="field" style="flex:1 1 220px" id="sf-token" placeholder="Setup token" aria-label="SimpleFIN setup token" autocomplete="off"><button class="btn primary" data-act="bank-connect"'+(S.busy?' disabled':'')+'>'+(S.busy==='connect'?'Connecting…':'Connect')+'</button></div>';
}
function dataCard(){
  return '<div class="head"><div><h2>Your data</h2><small>Everything is kept in one file, data/data.json, on the computer running this page. Nothing is sent anywhere else.</small></div></div>'+
   '<div class="toolbar"><button class="btn" data-act="import-csv">'+ic('upload')+'Import a bank statement (CSV)</button><a class="btn" href="api/export.csv" download="payments.csv">'+ic('download')+'Export payments</a><a class="btn" href="api/backup.json" download="finance-backup.json">'+ic('download')+'Download a backup</a></div>'+
   '<div class="sub">'+plural(S.txRaw.length,'payment')+' · '+plural(S.rules.length,'category rule')+' remembered'+(S.rules.length?' <button class="link" data-act="rules">Review</button>':'')+'</div>';
}

/* ---------- toast, forms, dialogs ---------- */
let toastT=0;
function toast(msg,undo){const t=$('toast');t.hidden=false;t.innerHTML='<span>'+esc(msg)+'</span>'+(undo?'<button id="toast-undo">Undo</button>':'');
  if(undo)$('toast-undo').onclick=()=>{t.hidden=true;undo()};clearTimeout(toastT);toastT=setTimeout(()=>{t.hidden=true},6000)}
async function save(p,ok){try{await p;if(ok)toast(ok);return true}catch(e){toast(e&&e.message||'Could not save. Check that the server is running and try again.');return false}}

function openForm(o){
  const d=$('dlg');d.className='';
  d.innerHTML='<form id="dlg-form"><h2>'+esc(o.title)+'</h2>'+o.fields.map(f=>{
    if(f.html)return f.html;
    const id='f-'+f.id,a=' id="'+id+'" name="'+f.id+'"'+(f.required===false?'':' required');
    const ctl=f.options?'<select'+a+'>'+f.options.map(x=>'<option'+(x===f.value?' selected':'')+'>'+esc(x)+'</option>').join('')+'</select>'
      :'<input'+a+' type="'+(f.type||'text')+'" value="'+esc(f.value==null?'':f.value)+'"'+(f.type==='number'?' step="any" min="'+(f.min==null?0:f.min)+'"'+(f.max?' max="'+f.max+'"':'')+' inputmode="decimal"':'')+(f.placeholder?' placeholder="'+esc(f.placeholder)+'"':'')+'>';
    return '<div class="fld"><label for="'+id+'">'+esc(f.label)+'</label>'+ctl+'</div>'}).join('')+
    '<div class="dlg-acts">'+(o.extra?'<button type="button" class="btn" id="dlg-extra">'+esc(o.extra.label)+'</button>':'')+'<div><button type="button" class="btn" id="dlg-cancel">Cancel</button><button class="btn primary" id="dlg-ok">'+esc(o.submit||'Save')+'</button></div></div></form>';
  $('dlg-cancel').onclick=()=>d.close();
  if(o.extra)$('dlg-extra').onclick=()=>{d.close();o.extra.run()};
  $('dlg-form').onsubmit=e=>{e.preventDefault();const v={};o.fields.forEach(f=>{if(!f.html)v[f.id]=$('f-'+f.id).value.trim()});d.close();o.onSubmit(v)};
  d.showModal();
}
function txFields(t){const c=cfg(),inc=t&&t.amount>0;return [
  {id:'desc',label:'What was it',placeholder:'Weekly shop',value:t?t.desc:''},{id:'amount',label:'Amount ('+c.currency+')',type:'number',value:t?Math.abs(t.amount):''},
  {id:'dir',label:'Direction',options:['Money out','Money in'],value:inc?'Money in':'Money out'},{id:'category',label:'Category',options:CATS.concat('Income'),value:t?(inc&&t.category!=='Transfer'?'Income':t.category||'Other'):'Groceries'},
  {id:'date',label:'Date',type:'date',value:t?t.date:(S.month===YM?TODAY:S.month+'-01')},{id:'who',label:'Who',options:['Shared'].concat(c.members),value:t&&t.who&&c.members.includes(t.who)?t.who:'Shared'}]}
function txFromForm(v){const amt=Math.abs(parseFloat(v.amount));if(!(amt>0)||!/^\d{4}-\d\d-\d\d$/.test(v.date)){toast('Enter an amount and a date.');return null}
  const inc=v.dir==='Money in';return {date:v.date,desc:v.desc,amount:inc?amt:-amt,category:v.category==='Transfer'?'Transfer':inc?'Income':(v.category==='Income'?'Other':v.category),who:v.who==='Shared'?'':v.who}}
const ruleId=s=>'r-'+s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,80);

async function api(path,body){let r;try{r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})})}catch(e){throw{message:'Cannot reach the server.'}}
  const j=await r.json().catch(()=>({}));if(!r.ok)throw{message:j.error||'The server refused the request.'};return j}

let csvText='';
async function csvPreview(flip){
  let p;try{p=await api('api/import/csv',{text:csvText,flip,dry:true})}catch(e){return toast(e.message)}
  const d=$('dlg');d.className='wide';
  d.innerHTML='<form id="dlg-form"><h2>Import a statement</h2><div class="sub" id="csv-summary"><b>'+plural(p.new,'new payment')+'</b> found'+(p.duplicates?', '+plural(p.duplicates,'already here','already here')+' and skipped':'')+(p.unreadable?', '+plural(p.unreadable,'row')+' could not be read':'')+'.</div>'+
   '<div class="sub">Columns used: '+Object.keys(p.columns).map(k=>esc(k)+' from “'+esc(p.columns[k])+'”').join(', ')+'</div>'+
   '<div class="tablewrap"><table><thead><tr><th>Date</th><th style="text-align:left">Description</th><th>Category</th><th>Amount</th></tr></thead><tbody>'+p.preview.map(r=>'<tr><td>'+esc(r.date)+'</td><td style="text-align:left;white-space:normal">'+esc(r.desc)+'</td><td>'+esc(r.category)+'</td><td class="'+(r.amount>0?'in':'')+'">'+(r.amount>0?'+':'−')+fmt(Math.abs(r.amount))+'</td></tr>').join('')+'</tbody></table></div>'+
   '<label class="check"><input type="checkbox" id="csv-flip"'+(flip?' checked':'')+'>Amounts are reversed (this file shows spending as positive numbers)</label>'+
   '<div class="dlg-acts"><div><button type="button" class="btn" id="dlg-cancel">Cancel</button><button class="btn primary" id="dlg-ok"'+(p.new?'':' disabled')+'>Import '+plural(p.new,'payment')+'</button></div></div></form>';
  $('dlg-cancel').onclick=()=>d.close();
  $('csv-flip').onchange=e=>csvPreview(e.target.checked);
  $('dlg-form').onsubmit=async e=>{e.preventDefault();d.close();try{const r=await api('api/import/csv',{text:csvText,flip});await S.db.pull();toast('Imported '+plural(r.imported,'payment')+'. Check the categories on the Payments page.')}catch(err){toast(err.message)}};
  if(!d.open)d.showModal();
}

const col=n=>S.db.collection(n);
const ACT={
  prev(){S.month=shift(S.month,-1);S.noteIdx=0;S.anim='page';render()},
  next(){if(S.month<YM){S.month=shift(S.month,1);S.noteIdx=0;S.anim='page';render()}},
  view(id){if(!VIEWS.some(v=>v[0]===id))return;if(S.view!==id)S.anim='page';S.view=id;try{history.replaceState(null,'','#'+id)}catch(e){location.hash=id}render();window.scrollTo(0,0)},
  span(id){S.span=+id;S.anim='flow';render()},
  note(id){S.noteIdx+=+id;S.anim='note';render()},
  theme(){const order=['auto','light','dark'],next=order[(order.indexOf(themeNow())+1)%3];try{localStorage.setItem('theme',next)}catch(e){}
    if(next==='auto')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=next;const h=document.documentElement;h.classList.add('theming');clearTimeout(h._t);h._t=setTimeout(()=>h.classList.remove('theming'),500);render()},
  'add-tx'(){openForm({title:'Add payment',submit:'Add',fields:txFields(null),onSubmit(v){const t=txFromForm(v);if(t)save(col('transactions').add(t),'Payment added')}})},
  'edit-tx'(id){const t=S.txRaw.find(x=>x.id===id);if(!t)return;
    openForm({title:'Edit payment',fields:txFields(t).concat({html:'<label class="check"><input type="checkbox" id="remember">Always use this category for payments named like this</label>'}),
      extra:{label:'Delete',run(){ACT['del-tx'](id)}},
      async onSubmit(v){const n=txFromForm(v);if(!n)return;const rem=$('remember').checked&&n.desc;
        if(await save(col('transactions').doc(id).update(n),rem?'':'Payment updated')&&rem)save(col('rules').doc(ruleId(n.desc)).set({match:n.desc.toLowerCase(),category:n.category}),'Updated. “'+n.desc+'” will be filed under '+n.category+' from now on.')}})},
  'del-tx'(id){const t=S.txRaw.find(x=>x.id===id);if(!t)return;const body=Object.assign({},t);delete body.id;
    save(col('transactions').doc(id).delete()).then(ok=>{if(ok)toast('Payment deleted',()=>save(col('transactions').doc(id).set(body)))})},
  'add-rec'(){openForm({title:'Add a regular bill or payday',submit:'Add',fields:[
     {id:'name',label:'Name',placeholder:'Rent'},{id:'amount',label:'Amount each month',type:'number'},
     {id:'dir',label:'Type',options:['Bill (money out)','Payday (money in)'],value:'Bill (money out)'},
     {id:'day',label:'Day of the month',type:'number',min:1,max:31,value:1},{id:'category',label:'Category',options:BUDGET_CATS,value:'Housing'}],
    onSubmit(v){const amt=Math.abs(parseFloat(v.amount)),day=Math.min(31,Math.max(1,parseInt(v.day,10)||1));if(!(amt>0))return toast('Enter an amount.');
      const inc=v.dir.indexOf('Payday')===0;save(col('recurring').add({name:v.name,amount:inc?amt:-amt,day,category:inc?'Income':v.category}),'Added')}})},
  'del-rec'(id){const r=S.rec.find(x=>x.id===id);if(!r)return;const body=Object.assign({},r);delete body.id;
    save(col('recurring').doc(id).delete()).then(ok=>{if(ok)toast('Removed '+r.name,()=>save(col('recurring').doc(id).set(body)))})},
  pay(id){const r=S.rec.find(x=>x.id===id);if(!r)return;
    save(col('transactions').add({date:TODAY,desc:r.name,amount:+r.amount,category:r.category||(r.amount>0?'Income':'Other'),who:'',recId:r.id}),r.amount>0?'Marked received':'Marked paid')},
  'add-pot'(){openForm({title:'New savings pot',submit:'Create',fields:[{id:'name',label:'Saving for',placeholder:'Vacation'},{id:'target',label:'Target amount',type:'number'},{id:'saved',label:'Already saved',type:'number',value:0}],
    onSubmit(v){const t=parseFloat(v.target);if(!(t>0))return toast('Enter a target.');save(col('pots').add({name:v.name,target:t,saved:Math.max(0,parseFloat(v.saved)||0)}),'Pot created')}})},
  pot(id){const p=S.pots.find(x=>x.id===id);if(!p)return;openForm({title:'Add money to '+p.name,submit:'Move money',fields:[{id:'amount',label:'Amount to move from the joint balance',type:'number'}],
    extra:{label:'Remove pot',run(){const body=Object.assign({},p);delete body.id;save(col('pots').doc(id).delete()).then(ok=>{if(ok)toast('Removed '+p.name,()=>save(col('pots').doc(id).set(body)))})}},
    async onSubmit(v){const amt=parseFloat(v.amount);if(!(amt>0))return toast('Enter an amount.');
      if(await save(col('pots').doc(id).update({saved:(+p.saved||0)+amt})))save(col('transactions').add({date:TODAY,desc:'To '+p.name,amount:-amt,category:'Savings',who:'',potId:id}),'Moved '+fmt(amt)+' to '+p.name)}})},
  settings(){const c=cfg();openForm({title:'Settings',fields:[
     {id:'household',label:'Household name',value:c.household},
     {id:'currency',label:'Currency',options:Object.keys(LOCALE),value:c.currency},
     {id:'opening',label:'Opening balance, before the first payment recorded here'+(counted().length?' (not used while bank accounts are linked)':''),type:'number',min:-1e12,value:c.opening},
     {id:'members',label:'People, separated by commas',value:c.members.join(', ')},
     {html:'<div class="eyebrow" style="margin-top:6px">Monthly budgets (leave blank for none)</div><div class="two">'+BUDGET_CATS.map(k=>'<div class="fld"><label for="b-'+k+'">'+k+'</label><input id="b-'+k+'" type="number" min="0" step="any" inputmode="decimal" value="'+(S.budgets[k]&&S.budgets[k].limit||'')+'"></div>').join('')+'</div>'}],
    async onSubmit(v){const members=v.members.split(',').map(s=>s.trim()).filter(Boolean).slice(0,8);
      const writes=[{op:'set',col:'settings',id:'main',data:Object.assign({},S.settings||{},{household:v.household||DEF.household,currency:v.currency,opening:parseFloat(v.opening)||0,members:members.length?members:DEF.members})}];
      BUDGET_CATS.forEach(k=>{const lim=parseFloat($('b-'+k).value)||0,old=S.budgets[k]&&S.budgets[k].limit||0;if(lim!==old)writes.push(lim?{op:'set',col:'budgets',id:k,data:{limit:lim}}:{op:'delete',col:'budgets',id:k})});
      save(S.db.batch(writes),'Settings saved')}})},
  'clear-ask'(){S.confirmClear=true;render()}, 'clear-no'(){S.confirmClear=false;render()},
  async 'clear-yes'(){S.confirmClear=false;
    const writes=[].concat(S.txRaw.filter(t=>t.sample).map(t=>({op:'delete',col:'transactions',id:t.id})),S.pots.filter(p=>p.sample).map(p=>({op:'delete',col:'pots',id:p.id})),S.rec.filter(r=>r.sample).map(r=>({op:'delete',col:'recurring',id:r.id})),Object.keys(S.budgets).filter(k=>S.budgets[k].sample).map(k=>({op:'delete',col:'budgets',id:k})));
    if(S.settings&&S.settings.sample){const s=Object.assign({},S.settings,{opening:0,members:DEF.members});delete s.sample;writes.push({op:'set',col:'settings',id:'main',data:s})}
    save(S.db.batch(writes),'Examples cleared. Set your opening balance and names in Settings.')},
  'import-csv'(){const f=$('csv-file');f.value='';f.click()},
  async 'bank-connect'(){const t=$('sf-token').value.trim();if(!t)return toast('Paste the setup token first.');S.busy='connect';render();
    try{const r=await api('api/bank/connect',{setupToken:t});await S.db.pull();toast('Connected. '+plural(r.accounts,'account')+' and '+plural(r.added,'payment')+' fetched.')}catch(e){toast(e.message)}S.busy='';render()},
  async 'bank-sync'(){S.busy='sync';render();try{const r=await api('api/bank/sync');await S.db.pull();toast('Synced. '+plural(r.added,'new payment')+'.')}catch(e){toast(e.message)}S.busy='';render()},
  'bank-disc-ask'(){S.confirmDisc=true;render()},'bank-disc-no'(){S.confirmDisc=false;render()},
  async 'bank-disc-yes'(){S.confirmDisc=false;try{await api('api/bank/disconnect');await S.db.pull();toast('Bank connection removed.')}catch(e){toast(e.message)}render()},
  rules(){const d=$('dlg');d.className='';
    d.innerHTML='<form id="dlg-form"><h2>Category rules</h2><div class="list">'+S.rules.map(r=>'<div class="row" style="grid-template-columns:minmax(0,1fr) auto auto"><div class="t"><b>'+esc(r.match)+'</b><small>filed under '+esc(r.category)+'</small></div><span></span><button type="button" class="x" data-act="del-rule" data-id="'+esc(r.id)+'" aria-label="Forget rule for '+esc(r.match)+'">×</button></div>').join('')+'</div><div class="dlg-acts"><div><button type="button" class="btn" id="dlg-cancel">Close</button></div></div></form>';
    $('dlg-cancel').onclick=()=>d.close();if(!d.open)d.showModal()},
  async 'del-rule'(id){if(await save(col('rules').doc(id).delete(),'Rule forgotten')){if(S.rules.length)ACT.rules();else $('dlg').close()}}
};
document.addEventListener('click',e=>{const b=e.target.closest('[data-act]');if(!b||b.disabled)return;const a=b.dataset.act;if(ACT[a])ACT[a](b.dataset.id)});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('.row.click')){e.preventDefault();ACT['edit-tx'](e.target.dataset.id)}});
document.addEventListener('input',e=>{if(e.target.id==='q'){S.q=e.target.value;refreshTx()}});
document.addEventListener('change',e=>{const t=e.target;
  if(t.id==='fcat'){S.fcat=t.value;refreshTx()}
  else if(t.dataset&&t.dataset.acct)save(col('accounts').doc(t.dataset.acct).update({include:t.checked}),t.checked?'Counted in the joint balance':'Left out of the joint balance')
  else if(t.id==='csv-file'&&t.files[0]){const r=new FileReader();r.onload=()=>{csvText=String(r.result||'');csvPreview(false)};r.onerror=()=>toast('Could not read that file.');r.readAsText(t.files[0]);t.value=''}});
window.addEventListener('hashchange',()=>{const v=hashView();if(v!==S.view){S.view=v;S.anim='page';render()}});
let rz=0,lastW=0;const redraw=()=>{clearTimeout(rz);rz=setTimeout(()=>{const w=$('view').clientWidth;if(S.ready&&S.view==='overview'&&w!==lastW){lastW=w;drawChart(monthData(S.month))}},120)};
window.addEventListener('resize',redraw);if(window.ResizeObserver)new ResizeObserver(redraw).observe($('view'));

/* ---------- data: the server beside this page keeps everything in data/data.json ---------- */
function localDB(){
  let data={},ver=-1;const subs=[];
  const rid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,8);
  const snapDoc=(c,id)=>{const d=(data[c]||{})[id];return{id,exists:!!d,data:()=>d}};
  async function pull(){const r=await fetch('api/data',{cache:'no-store'});if(!r.ok)throw{message:'The server is not answering.'};const j=await r.json();
    if(j.version!==ver||JSON.stringify(j.bank)!==JSON.stringify(S.bank)){ver=j.version;data=j.collections||{};S.bank=j.bank||{};subs.forEach(f=>f())}}
  async function req(method,path,body){let r;try{r=await fetch(path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})}catch(e){throw{message:'Cannot reach the server. Nothing was saved.'}}
    if(!r.ok)throw{message:'The server refused the change.'};await pull()}
  const docRef=(c,id)=>({id,set:b=>req('PUT','api/doc/'+c+'/'+encodeURIComponent(id),b),update:b=>req('PATCH','api/doc/'+c+'/'+encodeURIComponent(id),b),delete:()=>req('DELETE','api/doc/'+c+'/'+encodeURIComponent(id))});
  const colRef=c=>({doc:id=>docRef(c,id||rid()),add:b=>req('PUT','api/doc/'+c+'/'+rid(),b),rows:()=>Object.keys(data[c]||{}).map(id=>Object.assign({id},data[c][id]))});
  return {doc:p=>{const a=p.split('/');return docRef(a[0],a[1])},collection:colRef,batch:w=>w.length?req('POST','api/batch',{writes:w}):Promise.resolve(),pull,onChange:f=>subs.push(f),get:(c,id)=>snapDoc(c,id)};
}
async function boot(){
  render();
  const db=localDB();S.db=db;
  db.onChange(()=>{const s=db.get('settings','main');S.settings=s.exists?s.data():null;S.txRaw=db.collection('transactions').rows();S.pots=db.collection('pots').rows();S.rec=db.collection('recurring').rows();
    S.accounts=db.collection('accounts').rows();S.rules=db.collection('rules').rows();const o={};db.collection('budgets').rows().forEach(d=>o[d.id]=d);S.budgets=o;schedule()});
  let down=false;
  async function tick(){try{await db.pull();if(!S.ready||down){if(!S.ready)S.anim='page';S.ready=true;down=false;S.note='';schedule()}}
    catch(e){if(!down){down=true;S.ready=true;S.note='Cannot reach the finances server. Retrying.';schedule()}}}
  await tick();setInterval(tick,4000);
}
boot();
})();
