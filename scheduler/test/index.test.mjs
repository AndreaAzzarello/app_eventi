import assert from 'node:assert/strict';
import { test } from 'node:test';
import { dispatch } from '../src/index.mjs';

const env = { GITHUB_TOKEN: 't0k', GITHUB_REPO: 'o/r', WORKFLOW: 'import-events.yml', REF: 'main' };

test('chiama workflow_dispatch con ref e auto=true', async () => {
  let call;
  const status = await dispatch(env, async (url, init) => ((call = { url, init }), new Response(null, { status: 204 })));
  assert.equal(status, 204);
  assert.equal(call.url, 'https://api.github.com/repos/o/r/actions/workflows/import-events.yml/dispatches');
  assert.equal(call.init.method, 'POST');
  assert.equal(call.init.headers.Authorization, 'Bearer t0k');
  assert.deepEqual(JSON.parse(call.init.body), { ref: 'main', inputs: { auto: 'true' } });
});

test('errore se GitHub non risponde 204', async () => {
  await assert.rejects(dispatch(env, async () => new Response('Bad credentials', { status: 401 })), /401.*Bad credentials/);
});

test('errore chiaro senza token', async () => {
  await assert.rejects(dispatch({ ...env, GITHUB_TOKEN: '' }, async () => assert.fail('non deve chiamare')), /GITHUB_TOKEN/);
});
