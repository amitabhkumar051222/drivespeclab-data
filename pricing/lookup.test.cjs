const assert = require("node:assert/strict");
const api = require("./lookup.js");
const data = {records: [
  {brand:"Toyota",model:"Camry",model_year:2026,trim:"LE",status:"needs_reverification",msrp_usd:29600,msrp_source:"https://example.com",verified_on:null},
  {brand:"Honda",model:"Civic Sedan",model_year:2026,trim:"LX",status:"verified",msrp_usd:24695,msrp_source:"https://example.com",verified_on:"2026-10-27"}
]};
assert.equal(api.findPrice(data,{brand:"Toyota",model:"Camry",year:2026,trim:"LE"}),null);
assert.equal(api.findPrice(data,{brand:"honda",model:"Civic Sedan",year:2026,trim:"LX"}).msrp_usd,24695);
assert.equal(api.findPrice(data,{brand:"Honda",model:"Civic Sedan",year:2027,trim:"LX"}),null);
assert.throws(()=>api.findPrice({},{}),/Invalid pricing feed/);
console.log("PASS pricing adapter tests");
