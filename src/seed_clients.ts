import fs from 'fs';
import path from 'path';
import { query } from './db';

async function main() {
  const csvPath = path.join(process.cwd(), 'db', 'clients.csv');
  if (!fs.existsSync(csvPath)) throw new Error(`Missing ${csvPath}`);
  const content = fs.readFileSync(csvPath, 'utf8').trim();
  const rows = content.split(/\r?\n/).map(l => l.split(',').map(s => s.trim()));
  // Expect header: client_id,client_name,vault_account_id
  if (!/^client_id,client_name,vault_account_id$/i.test(rows[0].join(','))) {
    throw new Error('CSV header must be: client_id,client_name,vault_account_id');
  }
  for (const [client_id, client_name, vault_account_id] of rows.slice(1)) {
    await query("insert into clients(client_id,client_name,vault_account_id) values($1,$2,$3) on conflict (client_id) do update set client_name=excluded.client_name, vault_account_id=excluded.vault_account_id",
      [client_id, client_name, vault_account_id]);
    console.log('Upserted', client_id);
  }
  console.log('Done.');
}
main().catch(e => { console.error(e); process.exit(1); });
