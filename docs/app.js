'use strict';
const $ = id => document.getElementById(id);
const num = n => new Intl.NumberFormat('pt-BR').format(n);
const decimal = n => Number.isFinite(n) ? n.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '—';
const pct = (n,d) => d ? decimal(100*n/d)+'%' : '—';
let source;
function total(rows) {
  return rows.reduce((a,r) => { for (const k of ['orders','reviewed','score_sum','low_scores']) a[k]+=r[k]; return a; },{orders:0,reviewed:0,score_sum:0,low_scores:0});
}
function scoreRow(label,value,max,count,color,suffix='') {
  const width=Number.isFinite(value) ? Math.max(0,Math.min(100,value/max*100)) : 0;
  return `<div class="score-row"><div class="score-label"><span>${label}</span><b>${decimal(value)}${suffix}</b></div><div class="track"><div class="bar ${color}" style="width:${width}%"></div></div><small>${num(count)} pedidos avaliados</small></div>`;
}
function render(){
  const rows=source.groups.filter(r=>(!$('state').value||r.state===$('state').value)&&(!$('month').value||r.month===$('month').value));
  const all=total(rows), on=total(rows.filter(r=>!r.is_late)), late=total(rows.filter(r=>r.is_late));
  $('orders').textContent=num(all.orders); $('late').textContent=pct(late.orders,all.orders);
  $('late-detail').textContent=num(late.orders)+' pedidos após a data prevista';
  $('on-score').textContent=decimal(on.reviewed?on.score_sum/on.reviewed:NaN);
  $('late-score').textContent=decimal(late.reviewed?late.score_sum/late.reviewed:NaN);
  $('on-detail').textContent=num(on.reviewed)+' pedidos avaliados';
  $('review-detail').textContent=num(late.reviewed)+' pedidos avaliados';
  $('scope').textContent=num(all.reviewed)+' avaliações no recorte';
  $('score-chart').innerHTML=scoreRow('No prazo',on.score_sum/on.reviewed,5,on.reviewed,'')+scoreRow('Com atraso',late.score_sum/late.reviewed,5,late.reviewed,'orange');
  $('low-chart').innerHTML=scoreRow('No prazo',100*on.low_scores/on.reviewed,100,on.reviewed,'','%')+scoreRow('Com atraso',100*late.low_scores/late.reviewed,100,late.reviewed,'orange','%');
  const months=[...new Set(rows.map(r=>r.month))].sort();
  const monthly=months.map(m=>{const r=rows.filter(r=>r.month===m);const n=total(r).orders;return {m,n,v:100*total(r.filter(r=>r.is_late)).orders/n};});
  const max=Math.max(10,...monthly.map(r=>r.v));
  $('trend').innerHTML=monthly.map(r=>`<div class="trend-col" tabindex="0" aria-label="${r.m}: ${decimal(r.v)}% atrasados, ${num(r.n)} pedidos" title="${r.m}: ${decimal(r.v)}% atrasados · ${num(r.n)} pedidos"><div class="trend-bar" style="height:${r.v/max*115}px"></div><span>${r.m.slice(5)}/${r.m.slice(2,4)}</span></div>`).join('');
  const states=[...new Set(rows.map(r=>r.state))].map(state=>{const r=rows.filter(r=>r.state===state);const n=total(r).orders,l=total(r.filter(r=>r.is_late)).orders;return {state,n,l,rate:l/n};}).filter(r=>r.n>=100).sort((a,b)=>b.rate-a.rate||a.state.localeCompare(b.state)).slice(0,8);
  $('states-table').innerHTML=states.length?states.map(r=>`<tr><td>${r.state}</td><td>${num(r.n)}</td><td>${num(r.l)}</td><td>${pct(r.l,r.n)}</td></tr>`).join(''):'<tr><td colspan="4">Nenhum estado com pelo menos 100 pedidos neste recorte.</td></tr>';
}
fetch('data.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{
 source=data;
 for(const [id,values] of [['state',[...new Set(data.groups.map(r=>r.state))].sort()],['month',[...new Set(data.groups.map(r=>r.month))].sort()]]){
  values.forEach(value=>{const o=document.createElement('option');o.value=value;o.textContent=value;$(id).append(o);});
  $(id).addEventListener('change',render);
 }
 $('reset').addEventListener('click',()=>{$('state').value='';$('month').value='';render();}); render();
}).catch(()=>{$('error').hidden=false;$('scope').textContent='Dados indisponíveis';});
