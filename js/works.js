/* gchgch — 포트폴리오 렌더러
   data/works.json 을 읽어 메인(#grid), 목록(works.html), 상세(work.html)를 그린다.
   데이터는 관리자(Pages CMS)에서 수정하면 자동 반영된다. 이 파일은 고칠 필요 없음. */
(function(){
  var CATS={brand:'Brand',graphic:'Graphic',digital:'Digital',space:'Space'};
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function pad(n){return(n<10?'0':'')+n}
  function img(src,alt,cls){
    return src?'<img src="'+esc(src)+'" alt="'+esc(alt)+'" loading="lazy">':'<div class="ph '+(cls||'')+' mono">Image</div>';
  }

  fetch('data/works.json',{cache:'no-cache'}).then(function(r){return r.json()}).then(function(data){
    var works=(Array.isArray(data)?data:(data.works||[])).filter(function(w){return w.published!==false});
    works.sort(function(a,b){return (b.date||'').localeCompare(a.date||'')});
    if(document.getElementById('grid')) renderGrid(works);
    if(document.getElementById('wd')) renderDetail(works);
  }).catch(function(){
    var g=document.getElementById('grid');if(g)g.innerHTML='<p class="works__empty mono">작업을 불러오지 못했습니다</p>';
  });

  function renderGrid(all){
    var grid=document.getElementById('grid');
    var limit=parseInt(grid.dataset.limit||'0',10);
    var filters=document.getElementById('filters');
    var count=document.getElementById('count');
    var used=Object.keys(CATS).filter(function(k){return all.some(function(w){return w.category===k})});
    filters.innerHTML='<button class="is-on" data-f="all">All</button>'+used.map(function(k){return'<button data-f="'+k+'">'+CATS[k]+'</button>'}).join('');

    function draw(f){
      var list=all.filter(function(w){return f==='all'||w.category===f});
      var total=list.length;
      if(limit) list=list.slice(0,limit);
      grid.innerHTML=list.length?list.map(function(w,i){
        var wide=(i%5===0);
        return '<a href="work.html?id='+encodeURIComponent(w.slug)+'" class="card'+(wide?' card--w':'')+' is-in">'+
          '<div class="card__img">'+img(w.cover,w.title,i%3===0?'ph--o':'')+'<span class="card__hover">과정 보기 →</span></div>'+
          '<div class="card__meta"><h3 class="card__t">'+esc(w.title)+'</h3><span class="mono card__c">'+esc(w.type||CATS[w.category]||'')+'</span></div></a>';
      }).join(''):'<p class="works__empty mono">아직 등록된 작업이 없습니다</p>';
      count.textContent=pad(total)+' Projects';
    }
    filters.addEventListener('click',function(e){
      var b=e.target.closest('button');if(!b)return;
      filters.querySelectorAll('button').forEach(function(x){x.classList.toggle('is-on',x===b)});
      draw(b.dataset.f);
    });
    draw('all');
  }

  function renderDetail(all){
    var id=new URLSearchParams(location.search).get('id');
    var i=all.findIndex(function(w){return w.slug===id});
    var w=all[i>-1?i:0];var el=document.getElementById('wd');
    if(!w){el.innerHTML='<p class="mono">작업을 찾을 수 없습니다</p>';return}
    var next=all[((i>-1?i:0)+1)%all.length];
    document.title=w.title+' — gchgch';
    var gal=(w.gallery||[]).filter(Boolean);
    el.innerHTML=
      '<a href="works.html" class="wd__back mono">← All Works</a>'+
      '<h1 class="wd__title">'+esc(w.title)+'</h1>'+
      '<dl class="wd__meta">'+
        '<div><dt class="mono">Client</dt><dd>'+esc(w.client||'—')+'</dd></div>'+
        '<div><dt class="mono">Category</dt><dd>'+esc(CATS[w.category]||'—')+'</dd></div>'+
        '<div><dt class="mono">Scope</dt><dd>'+esc(w.type||'—')+'</dd></div>'+
        '<div><dt class="mono">Year</dt><dd>'+esc((w.date||'').slice(0,4)||'—')+'</dd></div>'+
      '</dl>'+
      '<div class="wd__cover">'+img(w.cover,w.title,'ph--o')+'</div>'+
      '<div class="wd__body"><span class="mono" style="color:var(--orange)">Process</span><div>'+
        (w.summary?'<p class="wd__summary">'+esc(w.summary)+'</p>':'')+
        '<div class="wd__text">'+(w.body||'')+'</div>'+
      '</div></div>'+
      (gal.length?'<div class="wd__gallery">'+gal.map(function(s){return'<img src="'+esc(s)+'" alt="" loading="lazy">'}).join('')+'</div>':'')+
      (next&&next!==w?'<div class="wd__next"><span class="mono">Next</span><a href="work.html?id='+encodeURIComponent(next.slug)+'">'+esc(next.title)+' →</a></div>':'');
  }
})();
