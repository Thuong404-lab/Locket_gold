const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const code = fs.readFileSync(path.join(__dirname, '..', 'locket-gold-local.js'), 'utf8');
const baseline = () => ({
  subscriber: {
    original_app_user_id: 'offline-user',
    entitlements: { Other: { product_identifier: 'other', expires_date: null } },
    subscriptions: { other: { store: 'app_store' } },
    non_subscriptions: { kept: [] }
  }
});

function run(options = {}) {
  const results = [];
  const context = {
    $request: {
      url: options.url || 'https://api.revenuecat.com/v1/subscribers/offline-user',
      headers: options.headers || { 'User-Agent': 'Locket/2.70.0', Authorization: 'fake-token' }
    },
    $argument: options.argument === undefined ? 'enabled=true' : options.argument,
    $done(value) { results.push(JSON.parse(JSON.stringify(value))); }
  };
  if (!options.requestOnly) {
    context.$response = {
      status: options.status === undefined ? 200 : options.status,
      body: options.body === undefined ? JSON.stringify(baseline()) : options.body
    };
  }
  vm.runInNewContext(code, context, { timeout: 1000 });
  assert.equal(results.length, 1);
  return results[0];
}

test('rewrites only local Gold fields and preserves account/other purchases', () => {
  const before = Date.now();
  const data = JSON.parse(run().body);
  assert.equal(data.subscriber.original_app_user_id, 'offline-user');
  assert.deepEqual(data.subscriber.entitlements.Other, baseline().subscriber.entitlements.Other);
  assert.deepEqual(data.subscriber.subscriptions.other, baseline().subscriber.subscriptions.other);
  assert.deepEqual(data.subscriber.non_subscriptions, { kept: [] });
  const expiry = Date.parse(data.subscriber.entitlements.Gold.expires_date);
  assert.ok(expiry >= before + 86400000);
  assert.ok(expiry <= Date.now() + 86400000);
});

test('ignores other apps and missing identification', () => {
  for (const headers of [{}, { 'User-Agent': 'OtherApp/1.0' }, { 'User-Agent': 'NotLocket/1.0' }]) {
    assert.deepEqual(run({ headers }), {});
    assert.deepEqual(run({ headers, requestOnly: true }), {});
  }
});

test('accepts case-insensitive header names and exact Locket bundle', () => {
  assert.ok(run({ headers: { 'uSeR-aGeNt': 'com.locket.Locket/2.70.0' } }).body);
  assert.ok(run({ headers: { 'X-Client-Bundle-ID': 'com.locket.Locket' } }).body);
});

test('ignores other domains and endpoints', () => {
  for (const url of [
    'https://example.invalid/v1/subscribers/offline-user',
    'https://api.revenuecat.com.example.invalid/v1/subscribers/offline-user',
    'https://api.revenuecat.com/v1/subscribers/offline-user/other',
    'https://api.revenuecat.com/v1/product_entitlement_mapping'
  ]) assert.deepEqual(run({ url }), {});
});

test('ignores errors, unknown HTTP status and malformed JSON', () => {
  for (const status of [304, 401, 403, 500, 'unknown']) assert.deepEqual(run({ status }), {});
  for (const body of ['', '{', 'null', '[]', '{}', '{"subscriber":{}}']) {
    assert.deepEqual(run({ body }), {});
  }
  assert.ok(run({ status: 'HTTP/1.1 200 OK' }).body);
});

test('preserves an existing active Gold entitlement', () => {
  const data = baseline();
  data.subscriber.entitlements.Gold = {
    product_identifier: 'existing-gold',
    expires_date: new Date(Date.now() + 86400000).toISOString()
  };
  assert.deepEqual(run({ body: JSON.stringify(data) }), {});
});

test('reuses a known expired Gold product identifier', () => {
  const data = baseline();
  data.subscriber.entitlements.Gold = {
    product_identifier: 'existing-gold', expires_date: '2020-01-01T00:00:00Z'
  };
  const output = JSON.parse(run({ body: JSON.stringify(data) }).body);
  assert.equal(output.subscriber.entitlements.Gold.product_identifier, 'existing-gold');
});

test('request phase only removes ETag and preserves authentication/input', () => {
  const headers = {
    'User-Agent': 'Locket/2.70.0', 'x-RevenueCAT-Etag': 'old-tag',
    Authorization: 'fake-token', 'X-Real-IP': 'kept'
  };
  const original = { ...headers };
  assert.deepEqual(run({ headers, requestOnly: true }), {
    headers: { 'User-Agent': 'Locket/2.70.0', Authorization: 'fake-token', 'X-Real-IP': 'kept' }
  });
  assert.deepEqual(headers, original);
  assert.deepEqual(run({ requestOnly: true }), {});
});

test('supports an explicit off switch and rejects malformed controls', () => {
  for (const argument of ['enabled=false', '', 'invalid']) {
    assert.deepEqual(run({ argument }), {});
    assert.deepEqual(run({ argument, requestOnly: true }), {});
  }
});

test('completes without any networking, logging or storage API', () => {
  assert.ok(run().body);
  assert.doesNotMatch(code, /\$httpClient|\$task|\$persistentStore|\$prefs|\bfetch\s*\(|console\./);
});
