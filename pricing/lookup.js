/* DriveSpecLab pricing feed adapter — no guessed prices. */
(function (root) {
  "use strict";
  var BASE = "https://raw.githubusercontent.com/amitabhkumar051222/drivespeclab-data/main/pricing/vehicle-prices.json";
  function clean(v) { return String(v == null ? "" : v).trim().toLowerCase(); }
  function findPrice(data, selection) {
    if (!data || !Array.isArray(data.records)) throw new Error("Invalid pricing feed");
    var match = data.records.find(function (x) {
      return x.status === "verified" &&
        clean(x.brand) === clean(selection.brand) &&
        clean(x.model) === clean(selection.model) &&
        Number(x.model_year) === Number(selection.year) &&
        clean(x.trim) === clean(selection.trim) &&
        Number.isFinite(x.msrp_usd) && x.msrp_usd > 0 &&
        Boolean(x.msrp_source) && Boolean(x.verified_on);
    });
    return match || null;
  }
  function fetchPrice(selection, options) {
    options = options || {};
    var source = options.url || BASE;
    var timeout = options.timeout || 8000;
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, timeout) : null;
    return fetch(source, {cache: "no-store", signal: controller ? controller.signal : undefined})
      .then(function (r) { if (!r.ok) throw new Error("Pricing feed unavailable"); return r.json(); })
      .then(function (data) { return findPrice(data, selection); })
      .finally(function () { if (timer) clearTimeout(timer); });
  }
  var api = Object.freeze({findPrice: findPrice, fetchPrice: fetchPrice, feedUrl: BASE});
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.DSLPricing = api;
})(typeof window !== "undefined" ? window : null);
