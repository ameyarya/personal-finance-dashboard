/* Personal Finance Dashboard: front end. No build step, no dependencies.
   State lives in S, every page is rendered from it, and the server beside this file keeps the data. */
(function(){
'use strict';
const CATS=['Housing','Groceries','Utilities','Insurance','Transport','Dining','Shopping','Health','Pets','Kids','Fun','Travel','Savings','Other','Transfer'];
const BUDGET_CATS=CATS.filter(c=>c!=='Transfer');
const NEEDS=['Housing','Groceries','Utilities','Insurance','Transport','Health','Pets','Kids'];
const CATMETA={Housing:['home','c1'],Groceries:['bag','c2'],Utilities:['bolt','c3'],Transport:['bus','c4'],Dining:['cup','c5'],Shopping:['tag','c6'],Health:['heart','c6'],Kids:['kid','c4'],Fun:['star','c3'],Savings:['coins','c1'],Other:['dots','c0'],Transfer:['swap','c0'],Income:['down','c2'],Insurance:['bank','c4'],Pets:['heart','c1'],Travel:['spark','c5']};
const ICONS={shield:'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM8.5 12l2.5 2.5 4.5-5',grid:'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',swap:'M7 7h13M16 3l4 4-4 4M17 17H4M8 13l-4 4 4 4',cal:'M5 5h14v15H5zM5 10h14M9 3v4M15 3v4',
 pie:'M12 3a9 9 0 1 0 9 9h-9zM15 3.5A9 9 0 0 1 20.5 9H15z',jar:'M7 8h10l1 12H6zM9 4h6v4H9z',users:'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5a6 6 0 0 1 3.5 5.5',
 sliders:'M4 7h10M18 7h2M4 17h2M10 17h10M16 5v4M8 15v4',home:'M4 11l8-7 8 7M6 10v10h12V10',bag:'M6 8h12l-1 12H7zM9 8a3 3 0 0 1 6 0',bolt:'M13 3L5 14h6l-1 7 8-11h-6z',
 bus:'M6 4h12v13H6zM6 12h12M8 20v-3M16 20v-3',cup:'M5 8h11v5a5.5 5.5 0 0 1-11 0zM16 9h2a2 2 0 0 1 0 5h-2M8 3v2M12 3v2',tag:'M4 4h8l8 8-8 8-8-8zM8.5 8.5h.01',
 heart:'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z',kid:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8.5 14a4 4 0 0 0 7 0M9 9.5h.01M15 9.5h.01',
 star:'M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-3-5.4 3 1.1-6L3.2 9.4l6.1-.8z',coins:'M12 5c4 0 7 1.3 7 3s-3 3-7 3-7-1.3-7-3 3-3 7-3zM5 8v4c0 1.7 3 3 7 3s7-1.3 7-3V8M5 12v4c0 1.7 3 3 7 3s7-1.3 7-3v-4',
 dots:'M6 12h.01M12 12h.01M18 12h.01',down:'M12 4v14M6 12l6 6 6-6',spark:'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18',info:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5M12 8h.01',
 chart:'M5 20V10M12 20V4M19 20v-7',bank:'M4 10h16M6 10v8M10 10v8M14 10v8M18 10v8M3 20h18M12 3l9 5H3z',
 sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19',moon:'M20 14A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 10z',auto:'M12 3a9 9 0 1 0 0 18zM12 3a9 9 0 0 1 0 18',
 search:'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4',plus:'M12 5v14M5 12h14',send:'M21 3L3 11l7 3 3 7zM10 14l11-11',bell:'M6 16v-5a6 6 0 0 1 12 0v5l2 2H4zM10 21h4',
 card:'M3 6h18v12H3zM3 10h18M7 15h4',refresh:'M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6',
 upload:'M12 16V4M7 9l5-5 5 5M5 20h14',download:'M12 4v12M7 11l5 5 5-5M5 20h14'};
const ic=(n,col)=>'<svg class="ic" viewBox="0 0 24 24"'+(col?' style="color:var(--'+col+')"':'')+' aria-hidden="true"><path d="'+(ICONS[n]||ICONS.dots)+'"/></svg>';
const catIco=(c,col)=>{const m=CATMETA[c]||CATMETA.Other;return '<span class="ico">'+ic(m[0],col||m[1])+'</span>'};
const MAIN_TABS=4;
const VIEWS=[['overview','Overview','grid'],['cards','Cards','card'],['payments','Transactions','swap'],['bills','Bills','cal'],['budgets','Budgets','pie'],['insights','Insights','chart'],['household','Household','users'],['check','Data check','shield'],['accounts','Accounts','bank']];
const LOCALE={USD:'en-US',EUR:'en-IE',GBP:'en-GB',CAD:'en-CA',AUD:'en-AU',INR:'en-IN',SGD:'en-SG',AED:'en-AE',JPY:'ja-JP',MXN:'es-MX'};
const DEF={household:'Our household',currency:'USD',opening:0,members:['You','Partner']};
const pad=n=>String(n).padStart(2,'0');
const iso=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());
const NOW=new Date(), TODAY=iso(NOW), YM=TODAY.slice(0,7);
const fromStatements=()=>!!(S.settings&&S.settings.fiscalYear)||S.txRaw.some(t=>t.source==='statement'||t.source==='pdf');
const fyOf=()=>{if(!fromStatements()||!S.tx.length)return {lo:'0000-00',hi:YM};const ms=S.tx.filter(t=>t.date).map(t=>t.date.slice(0,7)).sort();return {lo:ms[0],hi:ms[ms.length-1]}};
const openDate=()=>(S.settings&&S.settings.openingDate)||'';
const hashView=()=>{const h=location.hash.slice(1);return VIEWS.some(v=>v[0]===h)?h:'overview'};
const S={session:{},sync:{},period:'month',cardIdx:0,flip:false,settings:null,txRaw:[],tx:[],budgets:{},rec:[],rules:[],ready:false,db:null,month:YM,view:hashView(),span:6,noteIdx:0,txMax:100,check:null,checkAt:0,note:'',confirmClear:false,q:'',fcat:'',anim:'page'};
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cfg=()=>Object.assign({},DEF,S.settings||{});
const daysIn=m=>new Date(+m.slice(0,4),+m.slice(5,7),0).getDate();
const shift=(m,n)=>{const d=new Date(+m.slice(0,4),+m.slice(5,7)-1+n,1);return d.getFullYear()+'-'+pad(d.getMonth()+1)};
const isYear=m=>String(m).length===4;
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const curMo=()=>S.period==='year'?S.month.slice(0,4):S.month;
const mName=(m,o)=>isYear(m)?m:new Date(+m.slice(0,4),+m.slice(5,7)-1,1).toLocaleDateString('en-US',o||{month:'long',year:'numeric'});
const mLong=m=>isYear(m)?m:mName(m,{month:'long'}), mShort=m=>isYear(m)?m:mName(m,{month:'short'});
const ord=n=>n+(n%100>10&&n%100<14?'th':['th','st','nd','rd'][n%10]||'th');
const dayDiff=(a,b)=>Math.round((new Date(a+'T12:00:00')-new Date(b+'T12:00:00'))/864e5);
const shortDate=d=>new Date(d+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric'});
function fmt(n,compact){const c=cfg().currency;try{return new Intl.NumberFormat(LOCALE[c]||'en-US',{style:'currency',currency:c,maximumFractionDigits:compact?1:0,notation:compact?'compact':'standard'}).format(n)}catch(e){return Math.round(n).toLocaleString()}}
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0);
const flows=a=>a.filter(t=>t.category!=='Transfer');
const isInc=t=>t.amount>0&&t.category!=='Transfer'&&!t.refund;
const outOf=a=>sum(flows(a).filter(t=>t.amount<0),t=>-t.amount)-sum(flows(a).filter(t=>t.refund&&t.amount>0),t=>+t.amount);
const incOf=a=>sum(flows(a).filter(isInc),t=>+t.amount);
const plural=(n,one,many)=>n+' '+(n===1?one:(many||one+'s'));

/* ---------- derived figures ---------- */
function derive(){S.tx=S.txRaw.filter(t=>t.date)}
const cashOnly=a=>S.tx.some(t=>t.cash)?a.filter(t=>t.cash&&(!openDate()||t.date>=openDate())):a;
const patchSettings=p=>S.settings?S.db.doc('settings/main').update(p):S.db.doc('settings/main').set(Object.assign({},DEF,p));
function savePrefs(){try{localStorage.setItem('prefs',JSON.stringify({period:S.period,month:S.month}))}catch(e){}
  if(S.db&&S.settings){const p=S.settings.prefs||{};if(p.period!==S.period||p.month!==S.month)patchSettings({prefs:{period:S.period,month:S.month}}).catch(()=>{})}}
function currentBalance(){return (+cfg().opening||0)+sum(cashOnly(S.tx),t=>+t.amount||0)}
function yearData(y){
  const mtx=S.tx.filter(t=>t.date.startsWith(y));
  const endBal=currentBalance()-sum(cashOnly(S.tx.filter(t=>t.date>y+'-12-31')),t=>+t.amount||0);
  let bal=endBal-sum(cashOnly(mtx),t=>+t.amount||0);
  const per=Array(13).fill(0);cashOnly(mtx).forEach(t=>{per[+t.date.slice(5,7)]+=+t.amount||0});
  const actual=[];for(let k=1;k<=12;k++){bal+=per[k];actual.push({d:k,v:bal})}
  return {mo:y,N:12,last:12,cur:false,mtx,actual,fc:[],marks:[],items:[],bal:endBal,unpaidOut:0,inc:incOf(mtx),out:outOf(mtx)};
}
function monthData(mo){
  if(isYear(mo))return yearData(mo);
  const N=daysIn(mo),cur=mo===YM,last=cur?+TODAY.slice(8):N;
  const mtx=S.tx.filter(t=>t.date.startsWith(mo));
  let bal=currentBalance()-sum(cashOnly(S.tx.filter(t=>t.date>=mo+'-01')),t=>+t.amount||0);
  const byDay=Array(N+2).fill(0); cashOnly(mtx).forEach(t=>{byDay[Math.min(+t.date.slice(8),N)]+=+t.amount||0});
  const actual=[]; for(let d=1;d<=last;d++){bal+=byDay[d];actual.push({d,v:bal})}
  const items=S.rec.map(r=>Object.assign({},r,{due:Math.min(+r.day||1,N),paid:mtx.some(t=>t.recId===r.id)})).sort((a,b)=>a.due-b.due);
  const fc=[],marks=[];
  if(cur&&last<N){let f=bal;fc.push({d:last,v:f});
    for(let d=last+1;d<=N;d++){f+=byDay[d];const due=items.filter(i=>!i.paid&&(i.due===d||(d===last+1&&i.due<=last)));due.forEach(i=>f+=+i.amount);fc.push({d,v:f});due.forEach(i=>marks.push({d,v:f,i}))}}
  const unpaidOut=sum(items.filter(i=>!i.paid&&i.amount<0),i=>-i.amount);
  return {mo,N,last,cur,mtx,actual,fc,marks,items,bal,unpaidOut,inc:incOf(mtx),out:outOf(mtx)};
}
function spendByCat(mtx){const o={};flows(mtx).forEach(t=>{if(t.amount<0||t.refund){const c=t.category||'Other';o[c]=(o[c]||0)-t.amount}});Object.keys(o).forEach(k=>{if(o[k]<=0)delete o[k]});return o}
function notices(m){
  const n=[],yr=isYear(m.mo),prev=yr?{mtx:[],mo:m.mo}:monthData(shift(m.mo,-1)),sp=spendByCat(m.mtx),mult=yr?12:1;
  if(m.cur){
    const before=outOf(prev.mtx.filter(t=>+t.date.slice(8)<=m.last));
    if(before>0&&m.out>0){const p=Math.round((m.out-before)/before*100);n.push({i:'swap',t:'Spending is '+(p>=0?'up ':'down ')+Math.abs(p)+'%',b:fmt(m.out)+' so far against '+fmt(before)+' by this day in '+mLong(prev.mo)+'.',v:'payments',a:'See transactions'})}
    const due=m.items.filter(i=>!i.paid&&i.amount<0);
    if(due.length)n.push({i:'cal',t:plural(due.length,'bill')+' still to pay',b:fmt(m.unpaidOut)+' goes out before the '+ord(m.N)+'. Next is '+esc(due[0].name)+' on the '+ord(due[0].due)+'.',v:'bills',a:'See bills'});
  }
  Object.keys(S.budgets).forEach(k=>{const l=(S.budgets[k].limit||0)*mult;if(l&&sp[k]>l)n.push({i:(CATMETA[k]||CATMETA.Other)[0],t:esc(k)+' is over budget',b:fmt(sp[k])+' spent against a budget of '+fmt(l)+', over by '+fmt(sp[k]-l)+'.',v:'budgets',a:'See budgets'})});
  const un=m.mtx.filter(t=>t.amount<0&&(t.category||'Other')==='Other').length;
  if(S.check&&S.check.checked&&!S.check.complete)n.push({i:'shield',t:'Your statements are not complete',b:'Some months are missing or a statement does not add up. The Data check page lists exactly which.',v:'check',a:'See data check'});
  if(un>=5)n.push({i:'tag',t:plural(un,'transaction')+' with no category',b:'Open a transaction to pick a category. Tick the box to remember it for next time.',v:'payments',a:'See transactions'});
  return n;
}

/* ---------- motion helpers ---------- */
const REDUCED=window.matchMedia&&matchMedia('(prefers-reduced-motion:reduce)');
function restart(el,cls){if(!el)return;el.classList.remove(cls);void el.offsetWidth;el.classList.add(cls)}
function countUp(root){if(REDUCED&&REDUCED.matches)return;
  root.querySelectorAll('[data-n]').forEach(el=>{const to=+el.dataset.n,t0=performance.now(),D=950;if(!isFinite(to))return;
    const f=t=>{if(!el.isConnected)return;const p=Math.min((t-t0)/D,1),e=1-Math.pow(1-p,4);el.textContent=fmt(to*e);if(p<1)requestAnimationFrame(f)};requestAnimationFrame(f)})}
function placePill(){const p=document.querySelector('.navpill'),b=Array.from(document.querySelectorAll('#nav button.on')).find(x=>x.offsetWidth>0);if(!p||!b)return;
  p.style.width=b.offsetWidth+'px';p.style.height=b.offsetHeight+'px';p.style.transform='translate('+b.offsetLeft+'px,'+b.offsetTop+'px)';
  if(!p.classList.contains('ready'))requestAnimationFrame(()=>requestAnimationFrame(()=>p.classList.add('ready')))}
window.addEventListener('resize',placePill);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(placePill);

/* ---------- rendering ---------- */
let raf=0; function schedule(){if(!raf)raf=requestAnimationFrame(()=>{raf=0;render()})}
const themeNow=()=>{let t='';try{t=localStorage.getItem('theme')||''}catch(e){}if(t!=='light'&&t!=='dark')t=(S.settings&&S.settings.theme)||'';if(t!=='light'&&t!=='dark')t=window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';return t};
function render(){
  derive(); const an=S.anim; S.anim='';
  const c=cfg(),m=monthData(curMo()),hr=NOW.getHours();
  $('date').textContent=NOW.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
  $('title').textContent=c.household; $('mlabel').textContent=S.period==='year'?S.month.slice(0,4):mName(S.month);
  document.querySelectorAll('#period button').forEach(b=>{const on=b.dataset.id===S.period;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)});
  if(an==='page'){restart($('mlabel'),'swap-in');restart($('greet'),'rise');restart($('lede'),'rise')}
  $('greet').textContent=S.view==='overview'?'Good '+(hr<12?'morning':hr<17?'afternoon':'evening'):VIEWS.find(v=>v[0]===S.view)[1];
  let lede='';
  if(S.ready&&!m.cur)lede='Looking back at '+mName(m.mo)+'.';
  else if(S.ready){const pay=m.items.find(i=>!i.paid&&i.amount>0&&i.due>=m.last),nb=m.items.filter(i=>!i.paid&&i.amount<0&&(!pay||i.due<=pay.due)).length;
    lede=(pay?pay.name+' lands '+(pay.due===m.last?'today':'in '+plural(pay.due-m.last,'day'))+'. ':'')+(nb?plural(nb,'bill')+(nb===1?' goes':' go')+' out '+(pay?'before then.':'before the month ends.'):pay?'No bills are due before then.':'Nothing is due for the rest of the month.')}
  if(S.ready&&S.view==='cards'){const cs=cardList(m);lede=cs.length?plural(cs.length,'card')+' · '+fmt(sum(cs,c=>c.spent))+' spent on '+(cs.length===1?'it':'them')+' in '+mLong(m.mo):'No cards found in the statements yet.'}
  $('lede').textContent=lede;
  {const b=fyOf(),y=S.period==='year';$('next').disabled=y?S.month.slice(0,4)>=b.hi.slice(0,4):S.month>=b.hi;$('prev').disabled=y?S.month.slice(0,4)<=b.lo.slice(0,4):S.month<=b.lo}
  $('ic-search').innerHTML=ic('search');$('btn-add').innerHTML=ic('plus');$('btn-bell').innerHTML=ic('bell');$('btn-sync').innerHTML=ic('refresh');$('btn-sync').classList.toggle('spin',!!(S.sync&&S.sync.running));
  if(SL.was&&!(S.sync&&S.sync.running)&&!SL.open)toast(S.sync.message||'Sync finished');SL.was=!!(S.sync&&S.sync.running);
  {const who=(S.session&&S.session.user)||c.household||'H';$('btn-account').textContent=who.split(/\s+/).map(w=>w[0]).join('').slice(0,2).toUpperCase();$('btn-account').title=(S.session&&S.session.user?S.session.user+' · ':'')+c.household;}
  $('btn-bell').classList.toggle('has',S.ready&&notices(m).length>0);
  const th=themeNow();$('btn-theme').innerHTML=ic(th==='light'?'sun':'moon');$('btn-theme').title='Switch to '+(th==='light'?'dark':'light')+' theme';$('btn-theme').setAttribute('aria-label',$('btn-theme').title);if(document.documentElement.dataset.theme!==th)document.documentElement.dataset.theme=th;
  const nv=$('nav');
  if(!nv.querySelector('button'))nv.innerHTML='<i class="navpill" aria-hidden="true"></i>'+VIEWS.map((v,i)=>'<button data-act="view" data-id="'+v[0]+'"'+(i>=MAIN_TABS?' data-more="1"':'')+'>'+ic(v[2])+'<span>'+v[1]+'</span></button>').join('')+'<button class="more-btn" data-act="more" aria-haspopup="true" aria-expanded="false">'+ic('dots')+'<span>More</span></button>';
  const inMore=VIEWS.findIndex(v=>v[0]===S.view)>=MAIN_TABS;nv.querySelector('.more-btn').classList.toggle('on',inMore);if(nv._v!==S.view){closeMore();nv._v=S.view}
  nv.querySelectorAll('button[data-id]').forEach(b=>{const on=b.dataset.id===S.view;b.classList.toggle('on',on);if(on)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
  placePill();
  const cm=m.cur?m:monthData(YM);
  if(S.settings&&S.settings.fiscalYear)$('safe').hidden=true;
  else{$('safe').hidden=false;$('safe').innerHTML='<span>Safe to spend</span><b>'+(S.ready?fmt(cm.bal-cm.unpaidOut):'…')+'</b><span>'+(S.ready?fmt(cm.unpaidOut)+' of bills still due · '+plural(cm.N-cm.last,'day')+' left':'Loading')+'</span>';}

  const nSample=S.txRaw.filter(t=>t.sample).length+S.rec.filter(r=>r.sample).length;
  const b=$('banner');
  if(S.note){b.hidden=false;b.className='banner';b.innerHTML='<span>'+esc(S.note)+'</span>'}
  else if(nSample){b.hidden=false;b.className='banner';
    b.innerHTML=S.confirmClear?'<span><b>Delete '+nSample+' example entries?</b> Your own entries stay.</span><span class="acts"><button class="btn sm" data-act="clear-no">Keep them</button><button class="btn sm primary" data-act="clear-yes">Delete examples</button></span>'
      :'<span><b>Example data.</b> These figures are made up so you can see how the page works. They are not your accounts.</span><span class="acts"><button class="btn sm" data-act="clear-ask">Clear examples</button></span>'}
  else b.hidden=true;

  const card=(cls,html,id)=>'<section class="card '+cls+'"'+(id?' id="'+id+'"':'')+'>'+html+'</section>';
  let h;
  if(!S.ready)h=card('','<div class="empty">Loading your figures…</div>');
  else if(S.view==='overview')h=card('s7',balanceCard(m),'c-balance')+card('s5',flowCard(),'c-flow')+card('s6',catsCard(m),'c-cats')+card('s6',txCard(m,6),'c-tx')+card('s6',noticedCard(m),'c-noticed')+card('s6',dueCard(m,5),'c-due');
  else if(S.view==='cards')h=card('s7',cardStack(m),'c-stack')+card('s5',cardDetail(m),'c-cdet')+card('s7',cardsList(m),'c-clist')+card('s5',cardPays(m),'c-cpay');
  else if(S.view==='payments')h=card('',txCard(m,0),'c-tx');
  else if(S.view==='bills')h=card('',dueCard(m,0),'c-due');
  else if(S.view==='budgets')h=card('',budgetsCard(m),'c-budgets');
  else if(S.view==='insights')h=card('s6',heatCard(m),'c-heat')+card('s6',splitCard(m),'c-split')+card('s7',trendCard(m),'c-trend')+card('s5',biggestCard(m),'c-biggest');
  else if(S.view==='household')h=card('',houseCard(m,c),'c-house');
  else if(S.view==='check')h=card('',checkCard(),'c-check');
  else h=card('s6',sourcesCard(),'c-sources')+card('s6',syncCard(),'c-sync')+card('',dataCard(),'c-data');
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
    const pm=shift(YM,-1),cut=pm+'-'+pad(Math.min(m.last,daysIn(pm))),was=currentBalance()-sum(cashOnly(S.tx.filter(t=>t.date>cut)),t=>+t.amount||0);
    if(was){const p=Math.round((m.bal-was)/Math.abs(was)*100);chg='<div class="sub" style="margin-top:6px"><span class="pill '+(p>=0?'ok':'warn')+'">'+(p>=0?'↑ ':'↓ ')+Math.abs(p)+'%</span> against a month ago</div>'}
  } else tiles=[['In',m.inc],['Out',m.out],['Kept',m.inc-m.out],isYear(m.mo)?['Transactions',m.mtx.length]:['Bills paid',m.items.filter(i=>i.paid&&i.amount<0).length]];
  const end=m.fc.length?m.fc[m.fc.length-1].v:null;
  return '<div class="head"><div><h2>'+(S.settings&&S.settings.fiscalYear?'Cash balance at the end of '+mLong(m.mo):m.cur?'Joint balance':'Balance at the end of '+mLong(m.mo))+'</h2><small>'+(S.settings&&S.settings.fiscalYear?'Wealthfront Cash and Bank of America':m.cur?'Spent, by period':mName(m.mo))+'</small></div></div>'+
   '<div class="balrow"><div><div class="big" id="balance" data-n="'+m.bal+'">'+fmt(m.bal)+'</div>'+chg+'</div><div class="tiles">'+tiles.map(t=>'<div class="tile"><span>'+t[0]+'</span><b'+(t[0]==='Bills paid'||t[0]==='Transactions'?'>'+t[1]:' data-n="'+t[1]+'">'+fmt(t[1]))+'</b></div>').join('')+'</div></div>'+
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
  [1,Math.round(m.N/4),Math.round(m.N/2),Math.round(m.N*3/4),m.N].forEach((d,i)=>{s+='<text class="axis" x="'+x(d)+'" y="'+(H-5)+'" text-anchor="'+(i===0?'start':i===4?'end':'middle')+'">'+(isYear(m.mo)?MON[d-1]:d)+'</text>'});
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
    tip.hidden=false;tip.innerHTML='<small>'+(isYear(m.mo)?esc(MON[best.p.d-1]+' end'):esc(mShort(m.mo))+' '+best.p.d)+(best.f?' · forecast':'')+'</small><b>'+esc(fmt(best.p.v))+'</b>';
    const tw=tip.offsetWidth;tip.style.left=Math.min(Math.max(cx*(r.width/W),tw/2),r.width-tw/2)+'px';tip.style.top=Math.max(cy*(r.height/H)-8,0)+'px'};
  el.onmouseleave=off;
}

function flowCard(){
  const ms=[];const endM=S.period==='year'?S.month.slice(0,4)+'-12':S.month;for(let i=S.span-1;i>=0;i--)ms.push(shift(endM,-i));
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
  return m.mtx.filter(t=>(!S.fcat||(isInc(t)?'Income':t.category||'Other')===S.fcat)&&(!q||((t.desc||'')+' '+(t.category||'')+' '+(t.who||'')).toLowerCase().includes(q)))
    .sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:(a.id<b.id?1:-1))}
function rowPickers(t,cat){
  const c=cfg(),cats=CATS.concat('Income'),who=t.who||'',people=['Shared'].concat(c.members);if(who&&!c.members.includes(who))people.push(who);
  if(!cats.includes(cat))cats.push(cat);
  const sel=(f,list,cur,label)=>'<select class="rs" data-f="'+f+'" data-id="'+esc(t.id)+'" aria-label="'+label+' for '+esc(t.desc||'transaction')+'">'+list.map(o=>'<option'+(o===cur?' selected':'')+'>'+esc(o)+'</option>').join('')+'</select>';
  return '<div class="rowctl">'+sel('category',cats,cat,'Category')+sel('who',people,who||'Shared','Person')+'</div>'}
function txRows(list,full){
  if(!list.length)return '<div class="empty">'+(S.q||S.fcat?'No transactions match.':'No transactions recorded for '+mLong(curMo())+'. Use Add transaction to enter the first one, or sync your statements.')+'</div>';
  const all=list,more=full&&list.length>S.txMax?list.length-S.txMax:0;if(more)list=list.slice(0,S.txMax);
  return '<div class="list">'+list.map(t=>{const dd=dayDiff(TODAY,t.date),when=dd===0?'Today':dd===1?'Yesterday':shortDate(t.date),cat=isInc(t)?'Income':(t.category||'Other');
    return '<div class="row'+(full?' click" data-act="edit-tx" data-id="'+esc(t.id)+'" tabindex="0" role="button':'')+'">'+catIco(cat)+'<div class="t"><b>'+esc(t.desc||'Transaction')+'</b><small>'+when+(full?'':' · '+esc(cat)+(t.who?' · '+esc(t.who):''))+(t.card?' · '+esc(t.card):'')+(t.refund?' · refund':'')+(t.note?' · '+esc(t.note):'')+'</small>'+(full?rowPickers(t,cat):'')+'</div><div class="amt '+(t.amount>0?'in':'')+'">'+(t.amount>0?'+':'−')+fmt(Math.abs(t.amount))+'</div><div class="acts">'+(full?'<button class="x" data-act="del-tx" data-id="'+esc(t.id)+'" aria-label="Delete '+esc(t.desc||'transaction')+'">×</button>':'')+'</div></div>'}).join('')+'</div>'+(more?'<div class="more"><button class="btn" data-act="more-tx">Show '+Math.min(more,100)+' more <small>('+more+' hidden)</small></button></div>':'');
}
function txCard(m,limit){
  if(limit){const list=m.mtx.slice().sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:0);
    return '<div class="head"><div><h2>Latest transactions</h2><small>Everyone, every account</small></div><button class="link" data-act="view" data-id="payments">See all</button></div>'+txRows(list.slice(0,limit),false)}
  const list=filtered(m);
  return '<div class="head"><div><h2>Transactions in '+mLong(m.mo)+'</h2><small id="tx-count">'+plural(list.length,'entry','entries')+' · in '+fmt(incOf(list))+' · out '+fmt(outOf(list))+'</small></div></div>'+
   '<div class="toolbar"><input type="search" id="q" placeholder="Search transactions" aria-label="Search transactions" value="'+esc(S.q)+'"><select id="fcat" aria-label="Category"><option value="">All categories</option>'+CATS.concat('Income').map(c=>'<option'+(c===S.fcat?' selected':'')+'>'+c+'</option>').join('')+'</select>'+
   '</div>'+
   '<div id="tx-list">'+txRows(list,true)+'</div>';
}
function refreshTx(){if(!$('tx-list'))return;const m=monthData(curMo()),list=filtered(m);$('tx-list').innerHTML=txRows(list,true);$('tx-count').textContent=plural(list.length,'entry','entries')+' · in '+fmt(incOf(list))+' · out '+fmt(outOf(list))}


/* ---------- data check: is every statement here, and does each one add up? ---------- */
const CHK_LABEL={ok:'Matches the statement',unverified:'Statement does not print both balances, so it could not be cross-checked',mismatch:'Does not add up',missing:'No statement'};
function checkCard(){
  const k=S.check,head=(t,s)=>'<div class="head"><div><h2>'+t+'</h2>'+(s?'<small>'+s+'</small>':'')+'</div></div>';
  if(!k)return head('Data check','Loading')+'<div class="empty">Checking your statements…</div>';
  if(!k.checked)return head('Data check','Not run yet')+'<div class="empty">Nothing has been checked yet. Open Accounts, press Sync now and choose a full re-read: each statement is then compared with the balances it prints.</div>';
  const c=k.counts,bad=c.missing+c.mismatch+c.unreadable+k.accounts.reduce((n,a)=>n+a.issues.filter(i=>['stale','nodate'].includes(i.kind)).length,0);
  let h=head('Data check',k.complete?'Every statement is here and every balance adds up':plural(bad||1,'thing')+' to look at');
  h+='<div class="hint" style="margin-top:0">'+ic(k.complete?'shield':'info','accent')+'<span>'+(k.complete?'<b>Complete.</b> No months are missing between your statements and each statement\'s opening balance plus its transactions equals the closing balance it prints.'
    :'<b>Not complete yet.</b> The items below are gaps or figures that do not match. Add the missing statements to the folder and sync again.')+'</span></div>';
  h+='<div class="chk-tiles" style="margin:12px 0">'+[['Statements',c.statements],['Add up',c.ok],['Not cross-checked',c.unverified],['Do not add up',c.mismatch],['Months missing',c.missing],['Unreadable',c.unreadable]].map(t=>'<div class="tile"><small>'+t[0]+'</small><b>'+t[1]+'</b></div>').join('')+'</div>';
  const items=k.problems.map(p=>'<b>'+esc(p.account)+'</b> — '+esc(p.text)).concat(k.accounts.flatMap(a=>a.issues.filter(i=>i.kind!=='late').map(i=>'<b>'+esc(a.name)+(a.person?' · '+esc(a.person):'')+'</b> — '+esc(i.text))));
  if(items.length)h+='<h3 style="margin:14px 0 6px">What needs attention</h3><div class="list">'+items.map(t=>'<div class="row"><div class="t"><small style="color:var(--text)">'+t+'</small></div></div>').join('')+'</div>';
  h+='<h3 style="margin:16px 0 6px">Month by month</h3>';
  h+=k.accounts.map(a=>'<div class="chk"><div class="chk-h"><b>'+esc(a.name)+'</b>'+(a.person?' <small>'+esc(a.person)+'</small>':'')+'<small> · '+esc(a.first)+' to '+esc(a.last)+'</small></div><div class="chk-g">'+
    a.cells.map(x=>'<span class="cell '+x.state+'" title="'+esc(x.mo+': '+(CHK_LABEL[x.state]||x.state))+'" aria-label="'+esc(x.mo+': '+(CHK_LABEL[x.state]||x.state))+'">'+x.mo.slice(5)+'</span>').join('')+'</div>'+
    a.issues.filter(i=>i.kind==='late').map(i=>'<div class="chk-n">'+esc(i.text)+'</div>').join('')+'</div>').join('');
  h+='<div class="chk-key"><span class="cell ok">ok</span> adds up <span class="cell unverified">··</span> not cross-checked <span class="cell mismatch">!</span> does not add up <span class="cell missing">–</span> missing</div>';
  return h;
}
async function loadCheck(){
  try{const j=await fetch('api/check',{cache:'no-store'}).then(r=>r.json()),was=JSON.stringify(S.check);S.check=j;S.checkAt=Date.now();
    if(JSON.stringify(j)!==was&&S.view==='check')render();else if(JSON.stringify(j)!==was&&S.view==='overview')render()}catch(e){}
}

function noticedCard(m){
  const n=notices(m),title='<h2 style="display:flex;gap:8px;align-items:center">'+ic('spark','accent')+'Noticed</h2>';
  if(!n.length)return '<div class="head">'+title+'</div><div class="empty">Nothing stands out this month.</div>';
  const i=((S.noteIdx%n.length)+n.length)%n.length,x=n[i];
  return '<div class="head"><div>'+title+'<small id="note-pos">'+(i+1)+' of '+n.length+'</small></div>'+(n.length>1?'<div style="display:flex;gap:6px"><button class="btn icon" data-act="note" data-id="-1" aria-label="Previous">‹</button><button class="btn icon" data-act="note" data-id="1" aria-label="Next">›</button></div>':'')+'</div>'+
   '<span class="ico">'+ic(x.i,'accent')+'</span><div class="note"><h3>'+x.t+'</h3><p>'+x.b+'</p></div><div><button class="link" style="padding-left:0" data-act="view" data-id="'+x.v+'">'+x.a+' →</button></div>'+
   '<div class="steps">'+n.map((_,k)=>'<i'+(k===i?' class="on"':'')+'></i>').join('')+'</div>';
}

function dueCard(m,limit){
  if(isYear(m.mo))return '<div class="head"><div><h2>'+(limit?'Coming up':'Bills and paydays')+'</h2><small>Repeats every month</small></div></div><div class="empty">Pick a single month to see its bills and paydays.</div>';
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
  return h+'<div>'+keys.map(k=>{const v=sp[k]||0,l=(S.budgets[k]&&S.budgets[k].limit||0)*(isYear(m.mo)?12:1),name='<b style="display:flex;gap:10px;align-items:center">'+catIco(k)+esc(k);
    if(!l)return '<div class="cat" data-cat="'+esc(k)+'"><div class="l">'+name+'</b><span>'+fmt(v)+' · no budget</span></div><div class="bar nob"><i style="width:'+(v/mx*100).toFixed(1)+'%"></i></div></div>';
    const r=v/l,over=r>1,fast=!over&&m.cur&&r>pace+.1;
    return '<div class="cat" data-cat="'+esc(k)+'"><div class="l">'+name+' '+(over?'<span class="pill bad">Over</span>':fast?'<span class="pill warn">Ahead of pace</span>':'')+'</b><span>'+fmt(v)+' of '+fmt(l)+'</span></div><div class="bar'+(over?' over':fast?' fast':'')+'"><i style="width:'+Math.min(r*100,100).toFixed(1)+'%"></i>'+(m.cur?'<u style="left:'+(pace*100).toFixed(1)+'%"></u>':'')+'</div></div>'}).join('')+'</div>';
}

function houseCard(m,c){
  const by={},inc={};flows(m.mtx).forEach(t=>{const k=t.who||'Shared';if(t.amount<0)by[k]=(by[k]||0)-t.amount;else if(!t.refund)inc[k]=(inc[k]||0)+ +t.amount});
  const names=Array.from(new Set(c.members.concat(Object.keys(by),Object.keys(inc)))),mx=Math.max.apply(0,names.map(n=>by[n]||0))||1;
  return '<div class="head"><div><h2>Who spent what</h2><small>'+mName(m.mo)+' · Shared covers transactions with no person set</small></div></div><div>'+
   names.map(n=>'<div class="cat"><div class="l"><b style="display:flex;gap:10px;align-items:center"><span class="av">'+esc(n.split(/\s+/).map(s=>s[0]).join('').slice(0,2).toUpperCase())+'</span>'+esc(n)+'</b><span>'+(inc[n]?'brought in '+fmt(inc[n])+' · ':'')+'spent '+fmt(by[n]||0)+'</span></div><div class="bar"><i style="width:'+((by[n]||0)/mx*100).toFixed(1)+'%"></i></div></div>').join('')+'</div>';
}

/* ---------- insights ---------- */
function heatCard(m){
  if(isYear(m.mo)){const by=Array(13).fill(0);flows(m.mtx).forEach(t=>{if(t.amount<0||t.refund)by[+t.date.slice(5,7)]-=t.amount});const mx=Math.max.apply(0,by)||1,top=by.indexOf(Math.max.apply(0,by));
    return '<div class="head"><div><h2>Spending by month</h2><small>'+(by[top]>0?'Heaviest month was '+MON[top-1]+' at '+fmt(by[top]):'Nothing spent yet')+'</small></div></div><div class="heat months" id="heat">'+MON.map((n,k)=>'<div title="'+esc(n+': '+fmt(by[k+1]))+'"><i style="opacity:'+(Math.max(by[k+1],0)/mx*.85).toFixed(2)+'"></i><span>'+n+'</span></div>').join('')+'</div>'}
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
  if(isYear(m.mo)){const sp=spendByCat(m.mtx),ks=Object.keys(sp).sort((a,b)=>sp[b]-sp[a]),tot=sum(ks,k=>sp[k])||1,mons=new Set(m.mtx.map(t=>t.date.slice(0,7))).size||1;
    return '<div class="head"><div><h2>Categories for the year</h2><small>'+m.mo+' totals, monthly average and share of spending</small></div></div>'+(ks.length?'<div class="tablewrap"><table><thead><tr><th>Category</th><th>Year</th><th>Average month</th><th>Share</th></tr></thead><tbody>'+ks.map(k=>'<tr><td>'+esc(k)+'</td><td>'+fmt(sp[k])+'</td><td>'+fmt(sp[k]/mons)+'</td><td>'+Math.round(sp[k]/tot*100)+'%</td></tr>').join('')+'</tbody></table></div>':'<div class="empty">Nothing spent in '+m.mo+'.</div>')}
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
  return '<div class="head"><div><h2>Biggest transactions</h2><small>'+mName(m.mo)+'</small></div></div>'+(list.length?txRows(list,false):'<div class="empty">Nothing spent yet.</div>');
}


/* ---------- cards: one face per card in the statements ---------- */
const FACES=[['#9db8ff','#5b6fd6'],['#c4a8ff','#6a4fd0'],['#8fd6ff','#3d86c6'],['#ffc98f','#c9703a'],['#ff9fb8','#bd4a72'],['#9fe3d4','#3a8f86'],['#c9d0dc','#6b7690']];
function cardList(m){
  const by={};
  const yr=m.mo.slice(0,4);S.tx.filter(t=>t.card&&!t.cash&&t.category!=='Transfer'&&t.date.startsWith(yr)).forEach(t=>{(by[t.card]||(by[t.card]=[])).push(t)});
  const lim=(S.settings&&S.settings.cardLimits)||{},meta=(S.settings&&S.settings.cardMeta)||{};
  return Object.keys(by).map(name=>{const all=by[name],mo=all.filter(t=>t.date.startsWith(m.mo));
    const months=new Set(all.map(t=>t.date.slice(0,7))).size||1,total=outOf(all);
    const big=all.filter(t=>t.amount<0).sort((a,b)=>a.amount-b.amount)[0];
    return {name,owner:(meta[name]&&meta[name].owner)||'Shared',all,mo,spent:outOf(mo),total,avg:total/months,n:all.length,limit:+lim[name]||0,big}})
    .sort((a,b)=>b.total-a.total).map((c,i)=>Object.assign(c,{face:FACES[i%FACES.length],i}));
}
function vstyle(pos){const vis=pos<3;return 'transform:translateY('+(pos*-14)+'px) scale('+(1-pos*.06)+');opacity:'+(vis?(pos===0?1:pos===1?.8:.55):0)+';z-index:'+(9-pos)+';pointer-events:'+(vis?'auto':'none')}
function cardsRefresh(){const st=$('cstack');if(S.view!=='cards'||!st){return render()}
  const m=monthData(curMo()),cs=cardList(m),n=cs.length||1,sel=((S.cardIdx%n)+n)%n;
  st.querySelectorAll('.vcard').forEach((el,i)=>{const pos=(i-sel+n)%n;el.style.cssText=vstyle(pos)+';--a:'+cs[i].face[0]+';--b:'+cs[i].face[1];el.classList.toggle('flip',pos===0&&S.flip);el.dataset.act=pos===0?'cflip':'csel'});
  document.querySelectorAll('.cnav .dots i').forEach((d,i)=>d.classList.toggle('on',i===sel));
  [['c-cdet',cardDetail],['c-clist',cardsList],['c-cpay',cardPays]].forEach(([id,f])=>{const el=$(id);if(el)el.innerHTML=f(m)});}
function cardStack(m){
  const cs=cardList(m);
  if(!cs.length)return '<div class="head"><div><h2>Cards</h2><small>Every card in your statements</small></div></div><div class="empty">No card transactions yet. Statements you import show up here, one card each.</div>';
  const n=cs.length,sel=((S.cardIdx%n)+n)%n,c=cs[sel];
  const face=cs.map((x,i)=>{const pos=(i-sel+n)%n;
    const recent=x.all.slice().sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:0).slice(0,4);
    return '<div class="vcard'+(pos===0&&S.flip?' flip':'')+'" data-act="'+(pos===0?'cflip':'csel')+'" data-id="'+i+'" tabindex="0" role="button" aria-label="'+esc(x.name)+'" style="'+vstyle(pos)+';--a:'+x.face[0]+';--b:'+x.face[1]+'"><div class="inner">'+
      '<div class="face front"><div class="vtop"><b>'+esc(x.name)+'<small class="own">'+esc(x.owner)+'</small></b><span class="nfc">'+ic('spark')+'</span></div><span class="chip"></span>'+
      '<div class="vbot"><div><small>Spent in '+mShort(m.mo)+'</small><b>'+fmt(x.spent)+'</b></div><div><small>This year</small><b>'+fmt(x.total,true)+'</b></div></div></div>'+
      '<div class="face back"><b>'+esc(x.name)+' · recent</b>'+(recent.length?recent.map(t=>'<div class="vrow"><span><i>'+esc(shortDate(t.date))+'</i>'+esc(t.desc||'Transaction')+'</span><span>'+(t.amount>0?'+':'−')+fmt(Math.abs(t.amount))+'</span></div>').join(''):'<div class="vrow"><span>No transactions yet</span></div>')+'<small>Tap to flip back · swipe for the next card</small></div></div></div>'}).join('');
  return '<div class="head"><div><h2>Cards</h2><small>Tap the front card to flip it, tap the ones behind to bring them forward</small></div></div>'+
   '<div class="cstack" id="cstack">'+face+'</div>'+
   '<div class="cnav"><button class="btn icon" data-act="cnext" data-id="-1" aria-label="Previous card">‹</button><div class="dots">'+cs.map((_,i)=>'<i'+(i===sel?' class="on"':'')+'></i>').join('')+'</div><button class="btn icon" data-act="cnext" data-id="1" aria-label="Next card">›</button></div>';
}
function cardDetail(m){
  const cs=cardList(m);if(!cs.length)return '<div class="head"><h2>Card details</h2></div><div class="empty">Nothing to show yet.</div>';
  const c=cs[((S.cardIdx%cs.length)+cs.length)%cs.length],left=c.limit?c.limit-c.spent:null,r=c.limit?Math.min(c.spent/c.limit,1):0;
  return '<div class="head"><div><h2>'+esc(c.name)+'</h2><small>'+esc(c.owner)+' · '+plural(c.n,'transaction')+' in this year\'s statements</small></div>'+(c.limit&&c.spent>c.limit?'<span class="pill bad">Over limit</span>':'<span class="pill ok">On track</span>')+'</div>'+
   '<div class="tiles2"><div class="tile"><span>Spent in '+mLong(m.mo)+'</span><b>'+fmt(c.spent)+'</b></div><div class="tile"><span>'+(c.limit?'Left this month':'Average month')+'</span><b>'+fmt(c.limit?left:c.avg)+'</b></div></div>'+
   '<div class="tiles2"><div class="tile"><span>This year</span><b>'+fmt(c.total)+'</b></div><div class="tile"><span>Biggest transaction</span><b>'+(c.big?fmt(-c.big.amount):'—')+'</b></div></div>'+
   '<div class="fld"><label for="cowner">Owner</label><select id="cowner" data-card="'+esc(c.name)+'">'+(function(){const o=['Shared'].concat(cfg().members);if(o.indexOf(c.owner)<0)o.push(c.owner);return o})().map(o=>'<option'+(o===c.owner?' selected':'')+'>'+esc(o)+'</option>').join('')+'</select></div>'+
   '<div class="cat"><div class="l"><b>Monthly limit</b><span id="lim-out" class="in">'+(c.limit?fmt(c.limit):'None set')+'</span></div><input type="range" class="range" id="lim" data-card="'+esc(c.name)+'" min="0" max="10000" step="50" value="'+c.limit+'" aria-label="Monthly limit for '+esc(c.name)+'"><div class="bar'+(c.limit&&c.spent>c.limit?' over':'')+'"><i style="width:'+(r*100).toFixed(1)+'%"></i></div><small class="sub">A reminder only. It does not change anything with your bank.</small></div>';
}
function cardsList(m){
  const cs=cardList(m),sel=cs.length?((S.cardIdx%cs.length)+cs.length)%cs.length:0,mx=Math.max.apply(0,cs.map(c=>c.limit||c.spent))||1;
  return '<div class="head"><div><h2>All cards</h2><small>How far into the month each one is</small></div></div>'+(cs.length?'<div class="list">'+cs.map((c,i)=>
   '<div class="row click'+(i===sel?' cur':'')+'" data-act="csel" data-id="'+i+'" tabindex="0" role="button"><span class="mini" style="--a:'+c.face[0]+';--b:'+c.face[1]+'"></span><div class="t"><b>'+esc(c.name)+'</b><small>'+esc(c.owner)+' · '+plural(c.mo.length,'transaction')+' in '+mShort(m.mo)+'</small></div><div class="amt" style="min-width:150px"><div class="bar"><i style="width:'+Math.min(c.spent/mx*100,100).toFixed(1)+'%"></i></div><small class="sub">'+fmt(c.spent)+(c.limit?' of '+fmt(c.limit):'')+'</small></div><div></div></div>').join('')+'</div>':'<div class="empty">No cards yet.</div>');
}
function cardPays(m){
  const cs=cardList(m);if(!cs.length)return '<div class="head"><h2>Latest on this card</h2></div><div class="empty">No transactions yet.</div>';
  const c=cs[((S.cardIdx%cs.length)+cs.length)%cs.length],list=(c.mo.length?c.mo:c.all).slice().sort((a,b)=>a.date<b.date?1:-1).slice(0,8);
  return '<div class="head"><div><h2>'+esc(c.name)+' transactions</h2><small>The latest '+(c.mo.length?'in '+mLong(m.mo):'on this card')+'</small></div><button class="link" data-act="view" data-id="payments">All activity</button></div>'+txRows(list,false);
}

/* ---------- accounts and data ---------- */
function sourcesCard(){
  const by={};S.txRaw.forEach(t=>{const k=t.card||'Entered by hand',o=by[k]||(by[k]={n:0,out:0,inn:0,from:'9999',to:''});o.n++;if(t.category!=='Transfer'){if(t.amount<0)o.out-=t.amount;else if(isInc(t))o.inn+=t.amount}if(t.date<o.from)o.from=t.date;if(t.date>o.to)o.to=t.date});
  const ks=Object.keys(by).sort((a,b)=>by[b].n-by[a].n);
  const yrs=Array.from(new Set(S.txRaw.filter(t=>t.date).map(t=>t.date.slice(0,4)))).sort();
  let h='<div class="head"><div><h2>Where the figures come from</h2><small>'+(yrs.length?yrs[0]+(yrs.length>1?'–'+yrs[yrs.length-1]:'')+' · ':'')+plural(S.txRaw.length,'transaction')+'</small></div></div>';
  if(!ks.length)return h+'<div class="empty">Nothing loaded yet. Import a statement below, or run tools/import_statements.py.</div>';
  return h+'<div class="list">'+ks.map(k=>{const o=by[k];return '<div class="row"><span class="ico">'+ic('bank')+'</span><div class="t"><b>'+esc(k)+'</b><small>'+plural(o.n,'entry','entries')+' · '+shortDate(o.from)+' to '+shortDate(o.to)+'</small></div><div class="amt">'+(o.out?'−'+fmt(o.out):'')+'</div><div class="pct">'+(o.inn?'+'+fmt(o.inn):'')+'</div></div>'}).join('')+'</div>';
}
function syncCard(){
  const y=S.settings&&S.settings.sync||{},st=S.sync||{},when=st.lastRun?new Date(st.lastRun).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'';
  const warn=[];if(!st.pypdf)warn.push('Reading PDFs needs <b>pypdf</b>: <code>pip install pypdf</code>.');
  return '<div class="head"><div><h2>Statement sync</h2><small>Reads the PDF statements in a folder and adds any transactions that are missing</small></div><div class="toolbar"><button class="link" data-act="sl-open">View log</button><button class="btn primary sm" data-act="sync"'+(st.running?' disabled':'')+'>'+(st.running?'Syncing…':'Sync now')+'</button></div></div>'+
   (warn.length?'<div class="hint">'+ic('info','accent')+'<span>'+warn.join(' ')+'</span></div>':'')+
   '<div class="fld"><label for="sy-local">Statements folder on this Mac</label><div class="pick"><input id="sy-local" placeholder="/Users/you/Statements" spellcheck="false" value="'+esc(y.localFolder||'')+'"><button class="btn" data-act="pick-local">Choose…</button></div></div>'+
   '<div class="two"><div class="fld"><label for="sy-from">Keep transactions from year</label><input id="sy-from" type="number" min="1990" max="2100" placeholder="earliest" value="'+esc(y.fromYear||'')+'"></div><div class="fld"><label for="sy-to">to year</label><input id="sy-to" type="number" min="1990" max="2100" placeholder="latest" value="'+esc(y.toYear||'')+'"></div></div>'+
   '<div class="two"><div class="fld"><label for="sy-every">Check every (minutes)</label><input id="sy-every" type="number" min="5" step="5" value="'+esc(y.everyMinutes||60)+'"></div></div>'+
   '<label class="check"><input type="checkbox" id="sy-auto"'+(y.auto===false?'':' checked')+'>Check automatically while this computer is awake</label>'+
   '<div class="toolbar"><button class="btn" data-act="save-sync">Save</button></div>'+
   (when?'<div class="sub" id="sy-status">'+(st.ok===false?'<span class="err">'+esc(st.message||'')+'</span>':esc(st.message||''))+' <small>Last run '+when+'</small></div>':'<div class="sub" id="sy-status">Not run yet.</div>')+
   (st.unreadable&&st.unreadable.length?'<div class="sub"><small>Could not read: '+esc(st.unreadable.slice(0,5).join('; '))+(st.unreadable.length>5?' and '+(st.unreadable.length-5)+' more':'')+'</small></div>':'');
}
function dataCard(){
  return '<div class="head"><div><h2>Your data</h2><small>Everything is kept in one file, data/data.json, on the computer running this page. Nothing is sent anywhere else.</small></div></div>'+
   '<div class="toolbar"><a class="btn" href="api/backup.json" download="finance-backup.json">'+ic('download')+'Download a backup</a></div>'+
   '<div class="sub">'+plural(S.txRaw.length,'transaction')+' · '+plural(S.rules.length,'category rule')+' remembered'+(S.rules.length?' <button class="link" data-act="rules">Review</button>':'')+'</div>';
}

/* ---------- live sync window ---------- */
const SL={open:false,last:0,runId:'',timer:0,clock:0,running:false,was:false,opener:null,text:[]};
const slLine=x=>'<span class="l-'+x.l+'"><i>'+x.t+'</i>'+esc(x.m)+'</span>';
function slElapsed(){if(!SL.running||!SL.runId){$('sl-time').textContent='';return}const s=Math.max(0,Math.round((Date.now()-new Date(SL.runId).getTime())/1000));$('sl-time').textContent='Running for '+Math.floor(s/60)+':'+pad(s%60)}
async function slPoll(){
  let j;try{j=await fetch('api/sync/log?since='+SL.last,{cache:'no-store'}).then(r=>r.json())}catch(e){$('sl-state').textContent='Cannot reach the server.';return}
  const log=$('sl-log');
  if(j.last<SL.last||(j.started&&j.started!==SL.runId&&SL.runId)){SL.last=0;SL.text=[];log.innerHTML='';SL.runId=j.started||SL.runId;return slPoll()}
  SL.runId=j.started||SL.runId;
  if(j.lines.length){if(log.querySelector('.ph'))log.innerHTML='';log.insertAdjacentHTML('beforeend',j.lines.map(slLine).join('\n')+'\n');j.lines.forEach(x=>SL.text.push(x.t+' '+x.m));SL.last=j.last;if($('sl-follow').checked)log.scrollTop=log.scrollHeight}
  else if(!SL.text.length&&!j.running)log.innerHTML='<span class="l-info ph">Nothing has run yet. Press Run to start a sync.</span>';
  SL.running=j.running;
  $('sl-state').innerHTML=j.running?'<b>Running</b> · '+esc(j.phase||'working')+(j.total?' · '+j.done+' of '+j.total+' statements':''):(j.message?(j.ok===false?'<span class="err">Stopped or failed</span> · ':'<b>Finished</b> · ')+esc(j.message):'Idle');
  const bar=$('sl-bar');bar.classList.toggle('ind',j.running&&!j.total);$('sl-fill').style.width=j.total?Math.round(j.done/j.total*100)+'%':(j.running?'':(j.ok?'100%':'0%'));
  $('sl-step').textContent=j.running?(j.phase||''):'';
  $('sl-stop').disabled=!j.running;$('sl-run').disabled=j.running;$('sl-full').disabled=j.running;$('sl-run').textContent=j.running?'Running…':(SL.text.length?'Run again':'Run');
  slElapsed();
}
function openSyncLog(){const o=$('synclog');SL.opener=document.activeElement;SL.open=true;o.hidden=false;document.body.style.overflow='hidden';
  const y=S.settings&&S.settings.sync||{};$('sl-link').value=y.localFolder||'';$('sl-log').innerHTML='';SL.last=0;SL.text=[];SL.runId='';
  slPoll();clearInterval(SL.timer);SL.timer=setInterval(slPoll,700);clearInterval(SL.clock);SL.clock=setInterval(slElapsed,1000);$('sl-log').focus()}
function closeSyncLog(){SL.open=false;$('synclog').hidden=true;document.body.style.overflow='';clearInterval(SL.timer);clearInterval(SL.clock);if(SL.opener&&SL.opener.focus)try{SL.opener.focus()}catch(e){}}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&SL.open){e.preventDefault();closeSyncLog()}});
document.addEventListener('click',e=>{if(e.target.id==='synclog')closeSyncLog()});

/* ---------- swipe the card stack: left for the next card, right for the previous, tap to flip ---------- */
const SW={on:false,id:0,x0:0,y0:0,dx:0,t0:0,moved:false,el:null,lock:''};
const swipeBlockedClick=()=>SW.blockUntil&&performance.now()<SW.blockUntil;
document.addEventListener('pointerdown',e=>{const st=e.target.closest&&e.target.closest('#cstack');if(!st||e.button>0)return;const el=st.querySelector('.vcard[data-act="cflip"]');if(!el)return;
  Object.assign(SW,{on:true,id:e.pointerId,x0:e.clientX,y0:e.clientY,dx:0,t0:performance.now(),moved:false,el,lock:''})});
document.addEventListener('pointermove',e=>{if(!SW.on||e.pointerId!==SW.id)return;const dx=e.clientX-SW.x0,dy=e.clientY-SW.y0;
  if(!SW.lock){if(Math.abs(dx)<6&&Math.abs(dy)<6)return;SW.lock=Math.abs(dx)>Math.abs(dy)?'x':'y'}
  if(SW.lock==='y'){SW.on=false;return}
  if(!SW.moved){SW.moved=true;try{SW.el.setPointerCapture(e.pointerId)}catch(x){}SW.el.style.transition='none'}
  SW.dx=dx;SW.el.style.transform='translateX('+dx+'px) rotate('+(dx/28)+'deg)';SW.el.style.opacity=String(Math.max(.35,1-Math.abs(dx)/420));e.preventDefault()},{passive:false});
function swipeEnd(e){if(!SW.on||e.pointerId!==SW.id)return;SW.on=false;const el=SW.el,dx=SW.dx,v=Math.abs(dx)/Math.max(1,performance.now()-SW.t0);
  if(!SW.moved)return;SW.blockUntil=performance.now()+350;           // a drag must not also count as a tap
  const n=cardList(monthData(curMo())).length,go=n>1&&(Math.abs(dx)>70||(Math.abs(dx)>28&&v>.45));
  el.style.transition='transform .28s var(--ease),opacity .28s';
  if(!go){el.style.transform='';el.style.opacity='';return}
  const dir=dx<0?1:-1;el.style.transform='translateX('+(dx<0?-140:140)+'%) rotate('+(dx<0?-14:14)+'deg)';el.style.opacity='0';
  setTimeout(()=>{ACT.cnext(dir)},230)}
document.addEventListener('pointerup',swipeEnd);document.addEventListener('pointercancel',swipeEnd);
document.addEventListener('keydown',e=>{if((e.key==='ArrowLeft'||e.key==='ArrowRight')&&e.target.closest&&e.target.closest('.vcard'))ACT.cnext(e.key==='ArrowRight'?1:-1)});

/* ---------- the phone's "More" tab ---------- */
function closeMore(){const s=document.getElementById('more-sheet'),b=document.querySelector('.more-btn');if(s)s.hidden=true;if(b)b.setAttribute('aria-expanded','false')}
function toggleMore(){let s=document.getElementById('more-sheet');if(!s){s=document.createElement('div');s.id='more-sheet';s.setAttribute('role','menu');s.hidden=true;document.body.appendChild(s)}
  const open=s.hidden;if(!open)return closeMore();
  s.innerHTML=VIEWS.slice(MAIN_TABS).map(v=>'<button role="menuitem" data-act="view" data-id="'+v[0]+'"'+(v[0]===S.view?' class="on" aria-current="page"':'')+'>'+ic(v[2])+'<span>'+v[1]+'</span></button>').join('');
  s.hidden=false;restart(s,'in');document.querySelector('.more-btn').setAttribute('aria-expanded','true')}
document.addEventListener('click',e=>{const s=document.getElementById('more-sheet');if(s&&!s.hidden&&!e.target.closest('.more-btn'))closeMore()},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMore()});
window.addEventListener('resize',()=>{if(window.innerWidth>880)closeMore()});

/* ---------- search palette and popovers ---------- */
let palSel=0,palItems=[];
function palList(q){q=q.trim().toLowerCase();const out=[];
  VIEWS.forEach(v=>out.push({g:'Pages',t:v[1],i:v[2],run:()=>ACT.view(v[0])}));
  [['Add transaction','add-tx','plus'],['Add a bill or payday','add-rec','cal'],['Settings','settings','sliders'],['Switch theme','theme','sun']].forEach(a=>out.push({g:'Actions',t:a[0],i:a[2],run:()=>ACT[a[1]]()}));
  if(q){
    S.txRaw.filter(t=>((t.desc||'')+' '+(t.category||'')+' '+(t.who||'')).toLowerCase().includes(q)).sort((a,b)=>a.date<b.date?1:-1).slice(0,8)
      .forEach(t=>out.push({g:'Transactions',t:t.desc||'Transaction',s:shortDate(t.date)+' · '+(t.amount>0?'+':'−')+fmt(Math.abs(t.amount)),i:(CATMETA[t.category]||CATMETA.Other)[0],run:()=>{S.q=t.desc||'';S.fcat='';S.month=t.date.slice(0,7);ACT.view('payments')}}));
    S.rec.forEach(r=>out.push({g:'Bills',t:r.name,s:'Day '+r.day+' · '+fmt(Math.abs(r.amount)),i:'cal',run:()=>ACT.view('bills')}));
    return out.filter(x=>x.g==='Transactions'||(x.t+' '+(x.s||'')).toLowerCase().includes(q)).slice(0,14)}
  return out}
function palDraw(){const q=$('pal-q').value;palItems=palList(q);palSel=Math.min(palSel,Math.max(palItems.length-1,0));let g='',h='';
  palItems.forEach((x,k)=>{if(x.g!==g){g=x.g;h+='<div class="pal-g">'+g+'</div>'}
    h+='<button type="button" class="pal-i'+(k===palSel?' on':'')+'" data-k="'+k+'"><span class="ico">'+ic(x.i)+'</span><span class="t"><b>'+esc(x.t)+'</b>'+(x.s?'<small>'+esc(x.s)+'</small>':'')+'</span><kbd>↵</kbd></button>'});
  $('pal-list').innerHTML=h||'<div class="empty">Nothing matches “'+esc(q)+'”.</div>';
  const on=$('pal-list').querySelector('.on');if(on)on.scrollIntoView({block:'nearest'})}
function palRun(k){const x=palItems[k];if(!x)return;$('pal').close();setTimeout(x.run,60)}
function openPalette(){const d=$('pal');if(d.open)return;palSel=0;
  d.innerHTML='<div class="pal-in">'+ic('search')+'<input id="pal-q" type="text" placeholder="Search transactions, people, pages" autocomplete="off" aria-label="Search"><kbd>esc</kbd></div><div id="pal-list" class="pal-list"></div>';
  d.showModal();palDraw();$('pal-q').focus();
  $('pal-q').oninput=()=>{palSel=0;palDraw()};
  $('pal-q').onkeydown=e=>{if(e.key==='ArrowDown'){e.preventDefault();palSel=Math.min(palSel+1,palItems.length-1);palDraw()}else if(e.key==='ArrowUp'){e.preventDefault();palSel=Math.max(palSel-1,0);palDraw()}else if(e.key==='Enter'){e.preventDefault();palRun(palSel)}};
  $('pal-list').onclick=e=>{const b=e.target.closest('.pal-i');if(b)palRun(+b.dataset.k)};
  $('pal-list').onmousemove=e=>{const b=e.target.closest('.pal-i');if(b&&+b.dataset.k!==palSel){palSel=+b.dataset.k;$('pal-list').querySelectorAll('.pal-i').forEach(n=>n.classList.toggle('on',+n.dataset.k===palSel))}}}
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openPalette()}
  else if(e.key==='/'&&!/INPUT|TEXTAREA|SELECT/.test((e.target.tagName||''))&&!document.querySelector('dialog[open]')){e.preventDefault();openPalette()}
  else if(e.key==='Escape'&&!$('pop').hidden)closePop()});
if(!/Mac|iPhone|iPad/.test(navigator.platform||navigator.userAgent))$('kbd').textContent='Ctrl K';
let popKind='';
function closePop(){popKind='';const p=$('pop');if(p.hidden)return;p.classList.remove('in');p.hidden=true;$('btn-bell').setAttribute('aria-expanded','false');$('btn-account').setAttribute('aria-expanded','false');}
function togglePop(kind){if(popKind===kind)return closePop();const p=$('pop'),m=monthData(curMo());popKind=kind;let h='';
  if(kind==='bell'){const n=notices(m);h='<div class="pop-h">'+ic('spark','accent')+'<b>Noticed</b><small>'+n.length+'</small></div>'+(n.length?n.map(x=>'<button class="pop-i" data-act="view" data-id="'+x.v+'"><span class="ico">'+ic(x.i,'accent')+'</span><span class="t"><b>'+x.t+'</b><small>'+x.b+'</small></span></button>').join(''):'<div class="empty">Nothing stands out this month.</div>')}
  if(kind==='account')h=accountMenu();
  p.innerHTML=h;p.hidden=false;p.className=kind==='account'?'acc':'';restart(p,'in');$(kind==='bell'?'btn-bell':'btn-account').setAttribute('aria-expanded','true')}
document.addEventListener('click',e=>{if(popKind&&!e.target.closest('#pop,#btn-bell,#btn-account'))closePop();else if(popKind&&e.target.closest('#pop [data-act]'))closePop()},true);

/* ---------- account menu: who is signed in, passwords, sign-in on/off ---------- */
const initials=n=>String(n||'?').trim().split(/\s+/).map(w=>w[0]).join('').slice(0,2).toUpperCase();
function accountMenu(){
  const se=S.session||{},u=se.user,on=!!se.required,c=cfg(),has=new Set((se.users||[]).map(x=>x.toLowerCase())),people=c.members.slice();
  (se.users||[]).forEach(x=>{if(!people.some(p=>p.toLowerCase()===x.toLowerCase()))people.push(x)});
  const row=(n)=>{const me=u&&u.toLowerCase()===n.toLowerCase(),pw=has.has(n.toLowerCase());
    return '<div class="acc-p"><span class="av">'+esc(initials(n))+'</span><div class="t"><b>'+esc(n)+(me?' <span class="pill ok">You</span>':'')+'</b><small>'+(pw?'Can sign in':'No password yet')+'</small></div>'+
      (me?'<button class="btn sm" data-act="acc-pw">Change password</button>':(pw?'':'<button class="btn sm" data-act="acc-setup" data-id="'+esc(n)+'">Set password</button>'))+'</div>'};
  return '<div class="acc-h"><span class="avatar big">'+esc(initials(u||c.household))+'</span><div class="t"><b>'+esc(u||c.household)+'</b><small>'+(u?esc(c.household)+' · signed in':'Not signed in')+'</small></div></div>'+
   '<div class="acc-s '+(on?'ok':'warn')+'">'+ic(on?'info':'bolt',on?'accent':'out')+'<span>'+(on?'<b>Sign-in is on.</b> Everyone must sign in to open this page.':'<b>Sign-in is off.</b> Anyone on your home network can open this page.')+'</span></div>'+
   '<div class="pop-g">People</div>'+people.map(row).join('')+
   '<div class="pop-g">Account</div>'+
   (on?'':'<button class="pop-i" data-act="acc-on"><span class="ico">'+ic('bolt')+'</span><span class="t"><b>Turn on sign-in</b><small>Ask for a name and password</small></span></button>')+
   (u?'<button class="pop-i" data-act="acc-pw"><span class="ico">'+ic('sliders')+'</span><span class="t"><b>Change password</b></span></button>':'')+
   '<button class="pop-i" data-act="settings"><span class="ico">'+ic('sliders')+'</span><span class="t"><b>Household settings</b><small>Name, people, currency, budgets</small></span></button>'+
   (on?'<button class="pop-i" data-act="acc-off"><span class="ico">'+ic('info')+'</span><span class="t"><b>Turn off sign-in</b></span></button>':'')+
   (u?'<button class="pop-i danger" data-act="signout"><span class="ico">'+ic('down')+'</span><span class="t"><b>Sign out</b></span></button>':'');
}
function pwProblem(v,field){if((v[field]||'').length<(S.session&&S.session.minLength||8))return 'Use at least '+(S.session&&S.session.minLength||8)+' characters.';if(v.again!==undefined&&v[field]!==v.again)return 'The two passwords do not match.';return ''}
async function acctCall(path,body){try{await api(path,body);return ''}catch(e){return e.message}}
function setPasswordForm(name,first){
  const fields=(name?[]:[{id:'name',label:'Who is this for?',options:cfg().members,value:cfg().members[0]}]).concat([{id:'password',label:'Password',type:'password',autocomplete:'new-password'},{id:'again',label:'Type it again',type:'password',autocomplete:'new-password'}]);
  openForm({title:name?'Set a password for '+name:'Turn on sign-in',submit:name?'Save password':'Turn on',fields:fields,
    async run(v){const w=name||v.name,p=pwProblem(v,'password');if(p)return p;const m=await acctCall('api/account/setup',{name:w,password:v.password});if(m)return m;
      toast(first?'Sign-in is on':'Password saved');if(first)setTimeout(()=>location.reload(),400);else{S.session=await fetch('api/session').then(r=>r.json());render()}return ''}})}

let toastT=0;
function toast(msg,undo){const t=$('toast');t.hidden=false;t.innerHTML='<span>'+esc(msg)+'</span>'+(undo?'<button id="toast-undo">Undo</button>':'');
  if(undo)$('toast-undo').onclick=()=>{t.hidden=true;undo()};clearTimeout(toastT);toastT=setTimeout(()=>{t.hidden=true},6000)}
async function save(p,ok){try{await p;if(ok)toast(ok);return true}catch(e){toast(e&&e.message||'Could not save. Check that the server is running and try again.');return false}}

function openForm(o){
  const d=$('dlg');d.className='';
  d.innerHTML='<form id="dlg-form"><h2>'+esc(o.title)+'</h2>'+o.fields.map(f=>{
    if(f.html)return f.html;
    const id='f-'+f.id,a=' id="'+id+'" name="'+f.id+'"'+(f.required===false?'':' required')+(f.autocomplete?' autocomplete="'+f.autocomplete+'"':'');
    const ctl=f.options?'<select'+a+'>'+f.options.map(x=>'<option'+(x===f.value?' selected':'')+'>'+esc(x)+'</option>').join('')+'</select>'
      :'<input'+a+' type="'+(f.type||'text')+'" value="'+esc(f.value==null?'':f.value)+'"'+(f.type==='number'?' step="any" min="'+(f.min==null?0:f.min)+'"'+(f.max?' max="'+f.max+'"':'')+' inputmode="decimal"':'')+(f.placeholder?' placeholder="'+esc(f.placeholder)+'"':'')+'>';
    return '<div class="fld"><label for="'+id+'">'+esc(f.label)+'</label>'+ctl+'</div>'}).join('')+
    '<div class="err" id="dlg-err" role="alert"></div><div class="dlg-acts">'+(o.extra?'<button type="button" class="btn" id="dlg-extra">'+esc(o.extra.label)+'</button>':'')+'<div><button type="button" class="btn" id="dlg-cancel">Cancel</button><button class="btn primary" id="dlg-ok">'+esc(o.submit||'Save')+'</button></div></div></form>';
  $('dlg-cancel').onclick=()=>d.close();
  if(o.extra)$('dlg-extra').onclick=()=>{d.close();o.extra.run()};
  $('dlg-form').onsubmit=async e=>{e.preventDefault();const v={};o.fields.forEach(f=>{if(!f.html){const x=$('f-'+f.id).value;v[f.id]=f.type==='password'?x:x.trim()}});
    if(o.run){$('dlg-ok').disabled=true;const msg=await o.run(v);$('dlg-ok').disabled=false;if(msg){$('dlg-err').textContent=msg;return}d.close();return}
    d.close();o.onSubmit(v)};
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
  if(r.status===401&&!/api\/(login|account)/.test(path)){location.reload();throw{message:'Please sign in again.'}}
  const j=await r.json().catch(()=>({}));if(!r.ok)throw{message:j.error||'The server refused the request.'};return j}

async function pickFolder(){try{const r=await api('api/sync/pick',{});if(r.error){toast(r.error);return ''}return r.path||''}catch(e){toast(e.message);return ''}}
const col=n=>S.db.collection(n);
const ACT={
  more(){toggleMore()},
  account(){togglePop('account')},
  'acc-setup'(id){setPasswordForm(id,!(S.session&&S.session.required)&&!((S.session&&S.session.users)||[]).length)},
  'acc-on'(){setPasswordForm('',true)},
  'acc-pw'(){openForm({title:'Change password',submit:'Change password',fields:[{id:'current',label:'Current password',type:'password',autocomplete:'current-password'},{id:'password',label:'New password',type:'password',autocomplete:'new-password'},{id:'again',label:'Type the new one again',type:'password',autocomplete:'new-password'}],
    async run(v){const p=pwProblem(v,'password');if(p)return p;const m=await acctCall('api/account/password',{current:v.current,new:v.password});if(m)return m;toast('Password changed. Other devices will ask you to sign in again.');return ''}})},
  'acc-off'(){openForm({title:'Turn off sign-in',submit:'Turn off',fields:[{html:'<p class="sub">Anyone on your home network will be able to open this page without a password.</p>'},{id:'password',label:'Your password',type:'password',autocomplete:'current-password'}],
    async run(v){const m=await acctCall('api/account/require',{on:false,password:v.password});if(m)return m;toast('Sign-in is off');setTimeout(()=>location.reload(),400);return ''}})},
  async signout(){try{await api('api/logout',{})}catch(e){}location.reload()},
  async sync(){openSyncLog();try{await api('api/sync',{});slPoll()}catch(e){toast(e.message)}},
  'sl-open'(){openSyncLog()}, 'sl-close'(){closeSyncLog()}, 'sl-run'(){ACT.sync()},
  async 'sl-full'(){try{await api('api/sync',{force:true});slPoll()}catch(e){toast(e.message)}},
  async 'sync-stop'(){try{await api('api/sync/stop',{});toast('Stopping…');slPoll()}catch(e){toast(e.message)}},
  async 'sl-copy'(){const t=SL.text.join('\n');try{await navigator.clipboard.writeText(t);toast('Log copied')}catch(e){toast('Could not copy. Use Save log instead.')}},
  'sl-save'(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([SL.text.join('\n')+'\n'],{type:'text/plain'}));a.download='sync-log.txt';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),2000)},
  async 'sl-savelink'(){const v=($('sl-link').value||'').trim();const y=Object.assign({},S.settings&&S.settings.sync,{localFolder:v});await save(patchSettings({sync:y}),v?'Folder saved':'Folder cleared')},
  async 'sl-pick'(){const p=await pickFolder();if(p){$('sl-link').value=p;ACT['sl-savelink']()}},
  async 'pick-local'(){const p=await pickFolder();if(p)$('sy-local').value=p},
  'save-sync'(){const v=id=>($(id)&&$(id).value||'').trim(),every=Math.max(5,parseInt(v('sy-every'),10)||60);
    save(patchSettings({sync:{localFolder:v('sy-local'),everyMinutes:every,auto:$('sy-auto').checked,fromYear:v('sy-from'),toYear:v('sy-to')}}),'Sync settings saved')},
  csel(id){S.cardIdx=+id;S.flip=false;cardsRefresh()},
  cflip(){S.flip=!S.flip;cardsRefresh()},
  cnext(id){const n=cardList(monthData(curMo())).length||1;S.cardIdx=(((S.cardIdx+ +id)%n)+n)%n;S.flip=false;cardsRefresh()},
  palette(){openPalette()}, bell(){togglePop('bell')},
  prev(){const b=fyOf();if(S.period==='year'){if(S.month.slice(0,4)<=b.lo.slice(0,4))return;S.month=shift(S.month,-12)}else{if(S.month<=b.lo)return;S.month=shift(S.month,-1)}S.txMax=100;S.noteIdx=0;S.anim='page';savePrefs();render()},
  next(){const b=fyOf();if(S.period==='year'){if(S.month.slice(0,4)>=b.hi.slice(0,4))return;S.month=shift(S.month,12)}else{if(S.month>=b.hi)return;S.month=shift(S.month,1)}S.txMax=100;S.noteIdx=0;S.anim='page';savePrefs();render()},
  'more-tx'(){S.txMax+=100;refreshTx()},
  period(id){if(S.period===id)return;S.period=id==='year'?'year':'month';S.q=S.q;S.txMax=100;S.noteIdx=0;S.anim='page';savePrefs();render()},
  view(id){if(!VIEWS.some(v=>v[0]===id))return;S.txMax=100;if(S.view!==id)S.anim='page';S.view=id;try{history.replaceState(null,'','#'+id)}catch(e){location.hash=id}render();window.scrollTo(0,0)},
  span(id){S.span=+id;S.anim='flow';render()},
  note(id){S.noteIdx+=+id;S.anim='note';render()},
  theme(){const next=themeNow()==='dark'?'light':'dark';try{localStorage.setItem('theme',next)}catch(e){}
    document.documentElement.dataset.theme=next;const h=document.documentElement;h.classList.add('theming');clearTimeout(h._t);h._t=setTimeout(()=>h.classList.remove('theming'),500);if(S.db)patchSettings({theme:next}).catch(()=>{});render()},
  'add-tx'(){openForm({title:'Add transaction',submit:'Add',fields:txFields(null),onSubmit(v){const t=txFromForm(v);if(t)save(col('transactions').add(t),'Transaction added')}})},
  'edit-tx'(id){const t=S.txRaw.find(x=>x.id===id);if(!t)return;
    openForm({title:'Edit transaction',fields:txFields(t).concat({html:'<label class="check"><input type="checkbox" id="remember">Always use this category for transactions named like this</label>'}),
      extra:{label:'Delete',run(){ACT['del-tx'](id)}},
      async onSubmit(v){const n=txFromForm(v);if(!n)return;const rem=$('remember').checked&&n.desc;
        if(await save(col('transactions').doc(id).update(n),rem?'':'Transaction updated')&&rem)save(col('rules').doc(ruleId(n.desc)).set({match:n.desc.toLowerCase(),category:n.category}),'Updated. “'+n.desc+'” will be filed under '+n.category+' from now on.')}})},
  'del-tx'(id){const t=S.txRaw.find(x=>x.id===id);if(!t)return;const body=Object.assign({},t);delete body.id;
    save(col('transactions').doc(id).delete()).then(ok=>{if(ok)toast('Transaction deleted',()=>save(col('transactions').doc(id).set(body)))})},
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
  settings(){const c=cfg();openForm({title:'Settings',fields:[
     {id:'household',label:'Household name',value:c.household},
     {id:'currency',label:'Currency',options:Object.keys(LOCALE),value:c.currency},
     {id:'members',label:'People, separated by commas',value:c.members.join(', ')},
     {html:'<div class="eyebrow" style="margin-top:6px">Monthly budgets (leave blank for none)</div><div class="two">'+BUDGET_CATS.map(k=>'<div class="fld"><label for="b-'+k+'">'+k+'</label><input id="b-'+k+'" type="number" min="0" step="any" inputmode="decimal" value="'+(S.budgets[k]&&S.budgets[k].limit||'')+'"></div>').join('')+'</div>'}],
    async onSubmit(v){const members=v.members.split(',').map(s=>s.trim()).filter(Boolean).slice(0,8);
      const writes=[{op:'set',col:'settings',id:'main',data:Object.assign({},S.settings||{},{household:v.household||DEF.household,currency:v.currency,members:members.length?members:DEF.members})}];
      BUDGET_CATS.forEach(k=>{const lim=parseFloat($('b-'+k).value)||0,old=S.budgets[k]&&S.budgets[k].limit||0;if(lim!==old)writes.push(lim?{op:'set',col:'budgets',id:k,data:{limit:lim}}:{op:'delete',col:'budgets',id:k})});
      save(S.db.batch(writes),'Settings saved')}})},
  'clear-ask'(){S.confirmClear=true;render()}, 'clear-no'(){S.confirmClear=false;render()},
  async 'clear-yes'(){S.confirmClear=false;
    const writes=[].concat(S.txRaw.filter(t=>t.sample).map(t=>({op:'delete',col:'transactions',id:t.id})),S.rec.filter(r=>r.sample).map(r=>({op:'delete',col:'recurring',id:r.id})),Object.keys(S.budgets).filter(k=>S.budgets[k].sample).map(k=>({op:'delete',col:'budgets',id:k})));
    if(S.settings&&S.settings.sample){const s=Object.assign({},S.settings,{opening:0,members:DEF.members});delete s.sample;writes.push({op:'set',col:'settings',id:'main',data:s})}
    save(S.db.batch(writes),'Examples cleared. Set your names in Settings.')},
  rules(){const d=$('dlg');d.className='';
    d.innerHTML='<form id="dlg-form"><h2>Category rules</h2><div class="list">'+S.rules.map(r=>'<div class="row" style="grid-template-columns:minmax(0,1fr) auto auto"><div class="t"><b>'+esc(r.match)+'</b><small>filed under '+esc(r.category)+'</small></div><span></span><button type="button" class="x" data-act="del-rule" data-id="'+esc(r.id)+'" aria-label="Forget rule for '+esc(r.match)+'">×</button></div>').join('')+'</div><div class="dlg-acts"><div><button type="button" class="btn" id="dlg-cancel">Close</button></div></div></form>';
    $('dlg-cancel').onclick=()=>d.close();if(!d.open)d.showModal()},
  async 'del-rule'(id){if(await save(col('rules').doc(id).delete(),'Rule forgotten')){if(S.rules.length)ACT.rules();else $('dlg').close()}}
};
document.addEventListener('click',e=>{if(e.target.closest&&e.target.closest('.rowctl'))return;if(swipeBlockedClick()&&e.target.closest('#cstack')){e.preventDefault();e.stopPropagation();return}const b=e.target.closest('[data-act]');if(!b||b.disabled)return;const a=b.dataset.act;if(ACT[a])ACT[a](b.dataset.id)});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('.row.click,.vcard')){e.preventDefault();const a=e.target.dataset.act;if(ACT[a])ACT[a](e.target.dataset.id)}});
document.addEventListener('input',e=>{if(e.target.id==='lim'){$('lim-out').textContent=+e.target.value?fmt(+e.target.value):'None set'}if(e.target.id==='q'){S.q=e.target.value;S.txMax=100;refreshTx()}});
document.addEventListener('change',e=>{const t=e.target;
  if(t.id==='cowner'){const meta=Object.assign({},(S.settings&&S.settings.cardMeta)||{});meta[t.dataset.card]=Object.assign({},meta[t.dataset.card],{owner:t.value});save(patchSettings({cardMeta:meta}),'Owner saved');return}
  if(t.id==='lim'){const lim=Object.assign({},(S.settings&&S.settings.cardLimits)||{});lim[t.dataset.card]=+t.value;save(patchSettings({cardLimits:lim}));return}
  if(t.classList&&t.classList.contains('rs')){const tx=S.txRaw.find(x=>x.id===t.dataset.id);if(!tx)return;
    const p=t.dataset.f==='who'?{who:t.value==='Shared'?'':t.value}:{category:t.value};
    if(t.dataset.f==='category'&&t.value==='Income'&&tx.amount<0)p.amount=Math.abs(tx.amount);
    save(col('transactions').doc(tx.id).update(p),t.dataset.f==='who'?'Person saved':'Category saved');return}
  if(t.id==='fcat'){S.fcat=t.value;S.txMax=100;refreshTx()}});
window.addEventListener('hashchange',()=>{const v=hashView();if(v!==S.view){S.view=v;S.anim='page';render()}});
let rz=0,lastW=0;const redraw=()=>{clearTimeout(rz);rz=setTimeout(()=>{const w=$('view').clientWidth;if(S.ready&&S.view==='overview'&&w!==lastW){lastW=w;drawChart(monthData(curMo()))}},120)};
window.addEventListener('resize',redraw);if(window.ResizeObserver)new ResizeObserver(redraw).observe($('view'));

/* ---------- data: the server beside this page keeps everything in data/data.json ---------- */
function localDB(){
  let data={},ver=-1;const subs=[];
  const rid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,8);
  const snapDoc=(c,id)=>{const d=(data[c]||{})[id];return{id,exists:!!d,data:()=>d}};
  async function pull(){const r=await fetch('api/data',{cache:'no-store'});if(r.status===401){location.reload();throw{message:'Please sign in again.'}}if(!r.ok)throw{message:'The server is not answering.'};const j=await r.json();
    if(j.version!==ver||JSON.stringify(j.sync)!==JSON.stringify(S.sync)){ver=j.version;data=j.collections||{};S.sync=j.sync||{};subs.forEach(f=>f())}}
  async function req(method,path,body){let r;try{r=await fetch(path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})}catch(e){throw{message:'Cannot reach the server. Nothing was saved.'}}
    if(!r.ok)throw{message:'The server refused the change.'};await pull()}
  const docRef=(c,id)=>({id,set:b=>req('PUT','api/doc/'+c+'/'+encodeURIComponent(id),b),update:b=>req('PATCH','api/doc/'+c+'/'+encodeURIComponent(id),b),delete:()=>req('DELETE','api/doc/'+c+'/'+encodeURIComponent(id))});
  const colRef=c=>({doc:id=>docRef(c,id||rid()),add:b=>req('PUT','api/doc/'+c+'/'+rid(),b),rows:()=>Object.keys(data[c]||{}).map(id=>Object.assign({id},data[c][id]))});
  return {doc:p=>{const a=p.split('/');return docRef(a[0],a[1])},collection:colRef,batch:w=>w.length?req('POST','api/batch',{writes:w}):Promise.resolve(),pull,onChange:f=>subs.push(f),get:(c,id)=>snapDoc(c,id)};
}
async function boot(){
  try{S.session=await fetch('api/session',{cache:'no-store'}).then(r=>r.json())}catch(e){S.session={}}
  render();
  const db=localDB();S.db=db;
  db.onChange(()=>{const s=db.get('settings','main');S.settings=s.exists?s.data():null;S.txRaw=db.collection('transactions').rows();S.rec=db.collection('recurring').rows();
    S.rules=db.collection('rules').rows();const o={};db.collection('budgets').rows().forEach(d=>o[d.id]=d);S.budgets=o;schedule()});
  let down=false;
  async function tick(){try{await db.pull();if(S.view==='check'||Date.now()-S.checkAt>30000)loadCheck();if(!S.ready||down){if(!S.ready){S.anim='page';{const pr=S.settings&&S.settings.prefs;if(pr){S.period=pr.period==='year'?'year':'month';if(/^\d{4}-\d\d$/.test(pr.month||''))S.month=pr.month}}const ms=S.txRaw.filter(t=>t.date).map(t=>t.date.slice(0,7)).sort();if(ms.length&&!ms.includes(S.month))S.month=ms[ms.length-1]}S.ready=true;down=false;S.note='';schedule()}}
    catch(e){if(!down){down=true;S.ready=true;S.note='Cannot reach the finances server. Retrying.';schedule()}}}
  await tick();setInterval(tick,4000);
}
boot();
})();
