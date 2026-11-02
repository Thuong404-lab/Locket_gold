/* Local response experiment for Locket. Does not purchase or grant server access.
 * No HTTP calls, credential storage, notifications, or remote code loading.
 * The fallback product ID comes from the existing local Locket.js and has not
 * been verified against the user's current iPhone app.
 */
(function () {
  "use strict";

  function object(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function header(headers, name) {
    var keys = Object.keys(headers);
    for (var i = 0; i < keys.length; i += 1) {
      if (keys[i].toLowerCase() === name) return headers[keys[i]];
    }
    return "";
  }

  function rewrite() {
    if (typeof $argument !== "undefined" && $argument !== "enabled=true") return {};
    if (typeof $request === "undefined" || !object($request)) return {};
    if (!/^https:\/\/api\.revenuecat\.com\/v1\/(?:subscribers\/[^/?#]+|receipts)\/?(?:\?[^#]*)?$/.test($request.url || "")) return {};

    var headers = object($request.headers) ? $request.headers : {};
    var bundle = header(headers, "x-client-bundle-id");
    var agent = header(headers, "user-agent");
    var isLocket = bundle === "com.locket.Locket" ||
      (typeof agent === "string" && /^(?:com\.locket\.Locket|Locket(?:Widget| Camera)?)(?:\/|\s|$)/i.test(agent));
    if (!isLocket) return {};

    if (typeof $response === "undefined") {
      var nextHeaders = {};
      var changed = false;
      Object.keys(headers).forEach(function (key) {
        if (key.toLowerCase() === "x-revenuecat-etag") changed = true;
        else nextHeaders[key] = headers[key];
      });
      return changed ? { headers: nextHeaders } : {};
    }

    if (!object($response) || typeof $response.body !== "string") return {};
    var status = String($response.statusCode || $response.status || "");
    if (!/^(?:2\d\d(?:\s|$)|HTTP\/\S+\s+2\d\d(?:\s|$))/.test(status)) return {};

    var data = JSON.parse($response.body);
    if (!object(data) || !object(data.subscriber)) return {};
    var subscriber = data.subscriber;
    if (!object(subscriber.entitlements) || !object(subscriber.subscriptions)) return {};

    var previous = subscriber.entitlements.Gold;
    if (object(previous) && (previous.expires_date === null ||
        Date.parse(previous.expires_date) > Date.now())) return {};

    var product = object(previous) && typeof previous.product_identifier === "string" &&
      previous.product_identifier ? previous.product_identifier : "com.locket02.premium.yearly";
    var now = new Date();
    // A short test period, not a claim of a permanent subscription.
    var expiry = new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString();
    data.request_date = now.toISOString();
    data.request_date_ms = now.getTime();
    subscriber.entitlements.Gold = {
      product_identifier: product,
      purchase_date: now.toISOString(),
      expires_date: expiry
    };
    subscriber.subscriptions[product] = Object.assign({}, subscriber.subscriptions[product], {
      store: "app_store",
      ownership_type: "PURCHASED",
      period_type: "normal",
      is_sandbox: false,
      purchase_date: now.toISOString(),
      original_purchase_date: now.toISOString(),
      expires_date: expiry
    });
    return { body: JSON.stringify(data) };
  }

  var result = {};
  try { result = rewrite(); } catch (_) { /* Preserve the original on failure. */ }
  $done(result);
})();
