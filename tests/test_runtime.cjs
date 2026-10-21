const {JSDOM}=require(process.env.DSL_JSDOM_PATH || 'jsdom');
const assert=require('node:assert/strict'),fs=require('node:fs');
const data=JSON.parse(fs.readFileSync('data/catalog/cars.json'));
const dom=new JSDOM(`<head></head><body><section class="dslTrendingSection"><a href="/search/label/Honda#usmodel=CR-V"><h3>Honda CR-V</h3><span class="dslTrendPrice">$30,920</span></a></section><input id="dslKeyword"><button id="dslFindCars">Search</button><div id="dslHomeCompareModal" class="is-open"><select id="dslCompareCar1"><option value="spec-toyota-rav4">Toyota RAV4</option></select><select id="dslCompareCar2"><option value="spec-honda-cr-v">Honda CR-V</option></select><select id="dslCompareCar3"><option value="">None</option></select><div id="dslCompareTableWrap"></div></div></body>`,{url:'https://www.drivespeclab.com/',runScripts:'outside-only'});
const w=dom.window;w.DSL_CATALOG=data.cars;w.fetch=async()=>({ok:true,json:async()=>JSON.parse(fs.readFileSync('data/seo/model-routes-live.json'))});
let searches=0;w.document.querySelector('#dslFindCars').onclick=()=>searches++;
w.eval(fs.readFileSync('js/catalog-consistency.js','utf8'));
(async()=>{
 await new Promise(r=>setTimeout(r,300));
 const c=w.document.querySelector('.dslTrendingSection a');
 assert(c.textContent.includes('$31,520'));assert(c.textContent.includes('2027'));
 assert(c.href.endsWith('/2027-honda-cr-v-specs-price-mpg-dimensions.html'));
 assert(!w.DSL_CARS.some(c=>/Ram Ram|Toyota Toyota|Nissan Nissan/.test(c.name)));
 assert(w.DSL_CARS.find(c=>c.id==='spec-honda-cr-v').transmissions.includes('cvt'));
 w.document.querySelector('#dslKeyword').dispatchEvent(new w.Event('input'));
 await new Promise(r=>setTimeout(r,250));assert.equal(searches,1);
 const wrap=w.document.querySelector('#dslCompareTableWrap');assert(wrap.textContent.includes('Torque'));
 const trim=wrap.querySelector('[data-dsl-trim="spec-honda-cr-v"]');trim.value='1';trim.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert(wrap.textContent.includes('$33,550'));assert(wrap.textContent.includes('Not recorded for this trim'));
 // Idempotence avoids observer loops and protects user selections.
 const before=wrap.innerHTML;w.DSLConsistency.refresh();assert.equal(wrap.innerHTML,before);
 console.log('PASS: price/year, routes, display names, transmission, input search, trim comparison, idempotence');w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1;});
