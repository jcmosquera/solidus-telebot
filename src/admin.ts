import { query } from './db';
import { randomBytes, createHash } from 'crypto';

async function main() {
  const [cmd, clientId] = process.argv.slice(2);
  if (cmd === 'generate-link-code') {
    if (!clientId) throw new Error('Usage: ts-node src/admin.ts generate-link-code <client_id>');
    const code = randomBytes(8).toString('hex'); // share with the client
    const hash = createHash('sha256').update(code).digest('hex');
    const expires = new Date(Date.now() + 7*24*60*60*1000); // 7 days
    await query(
      "insert into link_codes(code_hash, client_id, expires_at) values($1,$2,$3) on conflict (code_hash) do nothing",
      [hash, clientId, expires.toISOString()]
    );
    console.log('One-time link code:', code);
  } else {
    console.log('Usage: ts-node src/admin.ts generate-link-code <client_id>');
  }
}
main().catch(e => { console.error(e); process.exit(1); });
