(()=>{'use strict';
  const key='riffle:saved:v1';
  const readSaved=()=>{try{return JSON.parse(localStorage.getItem(key)||'[]')}catch{return []}};
  const getSaved=()=>new Set(readSaved());
  const save=(value)=>{try{localStorage.setItem(key,JSON.stringify(Array.from(value)))}catch{}};
  const updateSaved=()=>{
    const saved=getSaved();
    const c=document.getElementById('saved-count'); if(c)c.textContent=String(saved.size);
    document.querySelectorAll('.bookmark-indicator').forEach(el=>{
      const paper=el.closest('[data-id]');if(!paper)return;
      const on=saved.has(paper.dataset.id);el.textContent=on?'★':'✧';el.classList.toggle('is-saved',on);
    });
    document.querySelectorAll('[data-save]').forEach(b=>{
      const on=saved.has(b.dataset.save);b.setAttribute('aria-pressed',String(on));
      b.querySelector('span').textContent=on?'保存済み':'あとで読む';b.firstChild.textContent=on?'★ ':'☆ ';
    });
  };
  updateSaved();
  document.querySelectorAll('[data-save]').forEach(button=>button.addEventListener('click',()=>{
    const saved=getSaved(),id=button.dataset.save;
    saved.has(id)?saved.delete(id):saved.add(id);save(saved);updateSaved();
  }));
  document.querySelectorAll('[data-share-url]').forEach(button=>button.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(window.location.href);const span=button.querySelector('span');span.textContent='コピーしました';setTimeout(()=>span.textContent='共有',1900)}catch{window.prompt('URLをコピー',location.href)}
  }));
  const input=document.getElementById('paper-search');
  if(!input)return;
  const cards=Array.from(document.querySelectorAll('#papers-grid .paper-card'));
  const filters=Array.from(document.querySelectorAll('[data-filter]'));
  const empty=document.getElementById('empty-state');
  const count=document.getElementById('result-count');
  let active='all';
  const apply=()=>{
    const q=input.value.trim().toLocaleLowerCase('ja');const saved=getSaved();let visible=0;
    cards.forEach(card=>{
      const matchText=card.dataset.search.includes(q);
      const matchType=active==='all'||active===card.dataset.type||(active==='saved'&&saved.has(card.dataset.id));
      const show=matchText&&matchType;card.hidden=!show;if(show)visible++;
    });
    count.textContent=String(visible);empty.hidden=visible>0;
  };
  input.addEventListener('input',apply);
  filters.forEach(button=>button.addEventListener('click',()=>{
    active=button.dataset.filter;
    filters.forEach(x=>x.classList.toggle('active',x===button));apply();
  }));
  document.querySelectorAll('[data-topic]').forEach(button=>button.addEventListener('click',()=>{
    input.value=button.dataset.topic;active='all';filters.forEach(x=>x.classList.toggle('active',x.dataset.filter==='all'));
    apply();document.getElementById('archive').scrollIntoView({behavior:'smooth'});input.focus({preventScroll:true});
  }));
  document.querySelectorAll('[data-nav-bookmarks]').forEach(a=>a.addEventListener('click',()=>{
    active='saved';filters.forEach(x=>x.classList.toggle('active',x.dataset.filter==='saved'));input.value='';apply();
  }));
  // CSS grid children use [hidden]—override display reliably.
  const style=document.createElement('style');style.textContent='.paper-card[hidden],.empty-state[hidden]{display:none!important}';document.head.appendChild(style);
  apply();
})();
