/* DriveSpecLab: shared catalog adapter for the existing Blogger theme. */
(function () {
  'use strict';
  if (window.DSLConsistency) return;
  var timer, observer, routes = {}, selectedTrims = {}, running = false;
  function q(s, root) { return (root || document).querySelector(s); }
  function qa(s, root) { return Array.from((root || document).querySelectorAll(s)); }
  function text(el, value) { if (el && el.textContent !== String(value)) el.textContent = String(value); }
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function norm(v) { return String(v || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
  function key(c) { return norm(c.brand) + '|' + norm(c.model); }
  function name(c) { return c.display_name || (String(c.model).toLowerCase().startsWith(c.brand.toLowerCase() + ' ') ? c.model : c.brand + ' ' + c.model); }
  function money(v) { return Number.isFinite(Number(v)) && Number(v) > 0 ? '$' + Number(v).toLocaleString('en-US') : 'Price not published'; }
  function route(c) {
    var r = routes[c.brand + '|' + c.model];
    // Never link a different model year, or an unconfirmed/predicted URL.
    if (r && r.url_status === 'live' && r.link_checked_on && String(r.year) === String(c.year) && /^https:\/\/www\.drivespeclab\.com\/20\d\d\//.test(r.url)) return r.url;
    return c.url || '/search/label/' + encodeURIComponent(c.brand === 'Land Rover' ? 'Land-Rover' : c.brand) + '#usmodel=' + encodeURIComponent(c.model);
  }
  function transmissions(v) {
    v = String(v || '').toLowerCase(); var out = [];
    if (/cvt|continuously variable/.test(v)) out.push('cvt');
    if (/manual/.test(v)) out.push('manual');
    if (/dct|dual.clutch/.test(v)) out.push('dct');
    if (/automatic|single.speed|direct drive/.test(v)) out.push('automatic');
    return out;
  }
  function catalog() {
    var seen = new Set();
    // The theme loads repository rows first, then old embedded fallback additions.
    return (window.DSL_CATALOG || []).filter(function (c) {
      if (!c || !c.brand || !c.model || seen.has(key(c))) return false;
      seen.add(key(c)); return true;
    });
  }
  function find(brand, model) { return catalog().find(function (c) { return key(c) === key({brand:brand, model:model}); }); }
  function fromLink(a) {
    try { var u = new URL(a.getAttribute('href'), location.href), m = u.pathname.match(/\/search\/label\/([^/]+)/);
      if (m && u.hash.startsWith('#usmodel=')) return find(decodeURIComponent(m[1]), decodeURIComponent(u.hash.slice(9)));
      return catalog().find(function (c) { return route(c) === u.href; });
    } catch (_) { return null; }
  }
  function syncIndex() {
    var cars = catalog(); if (!cars.length) return;
    window.DSL_CATALOG = cars;
    var old = new Map((window.DSL_CARS || []).map(function (c) { return [c.id, c]; }));
    window.DSL_CARS = cars.filter(function (c) { return !c.upcoming && (!c.market || c.market === 'US'); }).map(function (c) {
      var prior = old.get(c.id) || {}, tr = c.transmission || (c.details || {}).transmission || '';
      return Object.assign({}, prior, {id:c.id, brand:c.brand, model:c.model, name:name(c), year:c.year,
        price:c.starting_price, priceText:'Starting MSRP ' + money(c.starting_price), body:c.body_group || c.body,
        bodyRaw:c.body, powertrain:c.powertrain, fuels:c.fuel_types || [], drivetrain:c.drivetrain,
        seating:c.seating, keyDetail:c.key_detail, image:c.image || prior.image || '', url:route(c),
        source:c.source, verifiedOn:c.verified_on, details:c.details || {}, trims:c.trims || [],
        transmissionText:tr, transmissions:transmissions(tr), searchable:[name(c),c.year,c.body,c.powertrain,c.drivetrain,c.key_detail].join(' ').toLowerCase()});
    });
  }
  function syncCards() {
    qa('.dslTrendingSection a, #dslRecommendedGrid a, #dslBudgetCards a, #dslFinderResults a').forEach(function (a) {
      var c = fromLink(a); if (!c) return;
      if (a.getAttribute('href') !== route(c)) a.setAttribute('href', route(c));
      var card = a.closest('.finderCar') || a;
      text(q('h3,h4', card), name(c));
      var p = q('.dslTrendPrice,.finderPrice,.cw-cardbody p', card);
      if (p) text(p, money(c.starting_price));
      var heading = q('h3,h4', card);
      if (heading) {
        var year = q('.dslCatalogYear', card);
        if (!year) { year = document.createElement('small'); year.className = 'dslCatalogYear'; heading.after(year); }
        text(year, (c.year || 'Model year not recorded') + ' · U.S. model');
      }
    });
    qa('#dslCompareCar1 option,#dslCompareCar2 option,#dslCompareCar3 option').forEach(function (option) {
      var c = catalog().find(function (x) { return x.id === option.value; }); if (c) text(option, name(c) + (c.year ? ' (' + c.year + ')' : ''));
    });
  }
  function drawCompare() {
    var wrap = q('#dslCompareTableWrap'); if (!wrap || !q('#dslHomeCompareModal.is-open')) return;
    var ids = [1,2,3].map(function (i) { var el=q('#dslCompareCar'+i); return el && el.value; }).filter(Boolean);
    if (new Set(ids).size !== ids.length || ids.length < 2) return;
    var cars = ids.map(function (id) { return catalog().find(function (c) {return c.id===id;}); }).filter(Boolean);
    if (cars.length !== ids.length) return;
    var rows = [['Model year','year'],['Starting MSRP','price'],['Selected trim','trim'],['Body','body'],['Powertrain','powertrain'],['Drivetrain','drivetrain'],['Seats','seating'],['Engine / motor','engine'],['Power output','horsepower'],['Torque','torque'],['Transmission','transmission'],['Efficiency','efficiency'],['Electric range','range'],['Charging','charging'],['Cargo','cargo'],['Towing','towing'],['Dimensions','dimensions'],['Safety','safety'],['Warranty','warranty'],['Source data checked','verified_on']];
    function trim(c) { return (c.trims || [])[selectedTrims[c.id]]; }
    function val(c,k) { var t=trim(c); if(k==='price')return money(t ? t.msrp : c.starting_price); if(k==='trim')return t?t.name:'Model family'; if(t && (k==='powertrain'||k==='drivetrain'))return t[k]||'Not recorded for this trim'; return c[k] || (c.details || {})[k] || 'Not recorded'; }
    var html='<p class="dslCompareScope">Prices exclude destination, taxes and options unless stated by the source. Performance, efficiency and capability rows describe the model family; confirm the exact trim and drivetrain. Different model years are shown explicitly.</p><div class="dslCompareTrimGrid">';
    cars.forEach(function(c){html+='<label>'+esc(name(c))+' trim<select data-dsl-trim="'+esc(c.id)+'"><option value="">Model family</option>'+(c.trims||[]).map(function(t,i){return '<option value="'+i+'"'+(String(selectedTrims[c.id])===String(i)?' selected':'')+'>'+esc(t.name)+' · '+esc(money(t.msrp))+'</option>';}).join('')+'</select></label>';});
    html+='</div><table class="dslCompareTable"><thead><tr><th>Specification</th>'+cars.map(function(c){return '<th><strong>'+esc(name(c))+'</strong><br><a href="'+esc(route(c))+'">View specifications →</a></th>';}).join('')+'</tr></thead><tbody>';
    rows.forEach(function(r){ html+='<tr><th scope="row">'+r[0]+'</th>'+cars.map(function(c){return '<td>'+esc(val(c,r[1]))+'</td>';}).join('')+'</tr>'; });
    html+='<tr><th>Manufacturer source</th>'+cars.map(function(c){return '<td>'+(/^https:\/\//.test(c.source||'')?'<a href="'+esc(c.source)+'" target="_blank" rel="noopener">Check source ↗</a>':'Not recorded')+'</td>';}).join('')+'</tr></tbody></table>';
    if(wrap._dslContent!==html || !wrap.querySelector('.dslCompareScope')){wrap.innerHTML=html;wrap._dslContent=html;}
  }
  function cleanupModel() {
    var root=q('#dslVehicleDB .detail.on'); if(!root)return;
    qa('.v6Badge,.copy > small',root).forEach(function(el){if(/database.*v\d|v\d.*database/i.test(el.textContent))el.remove();});
    if(q('.dsl82SectionNav',root))qa('.dslModelTabs',root).forEach(function(el){el.remove();});
    var m=location.pathname.match(/\/search\/label\/([^/]+)/), c;
    try { if(m && location.hash.startsWith('#usmodel='))c=find(decodeURIComponent(m[1]),decodeURIComponent(location.hash.slice(9))); } catch(_){}
    if(!c)return;
    text(q('.copy h2',root),name(c)); text(q('.copy .price',root),money(c.starting_price));
    // Use the catalog record date, not a brand-wide compilation date.
    qa('.dsl82Badges span,.verified,.dslVerifiedLine span,.dslModelAside div,.dslModelAside span,.dslModelAside small',root).forEach(function(el){
      if(el.children.length)return;
      if(/^(?:✓ Official U\.S\. trim pricing verified|Verified:?|Data checked)\s+20\d\d-/.test(el.textContent.trim()))text(el,c.verified_on?'Source data checked '+c.verified_on:'Verification date not recorded');
    });
    var trimSection=q('#dsl82trims',root);
    qa('.dslModelActions a',root).forEach(function(a){if(trimSection && a.getAttribute('href')==='#dsl-trims')a.setAttribute('href','#dsl82trims');});
  }
  function refresh() {
    if(running)return; running=true;
    if(observer)observer.disconnect();
    syncIndex();syncCards();cleanupModel();drawCompare();
    if(observer)observer.observe(document.body,{childList:true,subtree:true});
    running=false;
  }
  function schedule(){clearTimeout(timer);timer=setTimeout(refresh,80);}
  function init(){
    var style=document.createElement('style');style.textContent='#dslVehicleDB .detail.on .dhero:before{content:none!important}.dslCatalogYear{display:block;color:#5b6c7a;font-size:11px;margin:3px 0 5px}.dslCompareScope{font-size:12px;line-height:1.6;color:#526579}.dslCompareTrimGrid{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.dslCompareTrimGrid label{flex:1;min-width:160px;font-size:12px}.dslCompareTrimGrid select{display:block;width:100%;padding:9px;margin-top:6px;border:1px solid #ccd8e4;border-radius:7px}';document.head.appendChild(style);
    observer=new MutationObserver(schedule);refresh();
    var input=q('#dslKeyword');if(input){input.setAttribute('aria-label','Search cars by brand or model');var debounce;input.addEventListener('input',function(){clearTimeout(debounce);debounce=setTimeout(function(){syncIndex();var b=q('#dslFindCars');if(b)b.click();},160);});}
    ['dslBudget','dslBody','dslFuel','dslTransmission'].forEach(function(id){var el=document.getElementById(id);if(el)el.addEventListener('change',function(){syncIndex();var b=q('#dslFindCars');if(b)b.click();});});
    document.addEventListener('click',function(e){if(e.target.closest('#dslFindCars,#dslStartCompare,#dslRunCompare')){syncIndex();schedule();}},true);
    document.addEventListener('change',function(e){if(e.target.matches('[data-dsl-trim]')){selectedTrims[e.target.dataset.dslTrim]=e.target.value===''?undefined:Number(e.target.value);drawCompare();}else if(e.target.matches('#dslCompareCar1,#dslCompareCar2,#dslCompareCar3'))schedule();});
    var base='https://raw.githubusercontent.com/amitabhkumar051222/drivespeclab-data/main/';
    fetch(base+'data/seo/model-routes-live.json',{cache:'no-cache'}).then(function(r){if(!r.ok)throw Error(r.status);return r.json();}).then(function(d){routes=d.routes||{};schedule();}).catch(function(){/* Keep working hash links when the route feed is unavailable. */});
  }
  window.DSLConsistency={version:1,refresh:refresh,displayName:name,transmissions:transmissions};
  ['dsl-db-ready','dsl-catalog-ready','dsl-catalog-enriched','hashchange'].forEach(function(e){window.addEventListener(e,schedule);});
  document.addEventListener('DriveSpecLabDBReady',schedule);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
