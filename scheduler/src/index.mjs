/** Avvia import-events.yml con workflow_dispatch (auto=true: il workflow salta se l'import di oggi è già partito). */
export async function dispatch(env, fetchFn = fetch) {
  if (!env.GITHUB_TOKEN) throw new Error('GITHUB_TOKEN mancante: npx wrangler secret put GITHUB_TOKEN');
  const url = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW}/dispatches`;
  const res = await fetchFn(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'eventi-vicini-scheduler'
    },
    body: JSON.stringify({ ref: env.REF, inputs: { auto: 'true' } })
  });
  if (res.status !== 204) throw new Error(`GitHub ha risposto ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.status;
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  }
};
