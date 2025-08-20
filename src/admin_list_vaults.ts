import { makeFireblocksClient } from './fireblocks';

async function main() {
  // Usage:
  //   ts-node src/admin_list_vaults.ts 2 PN06556148
  //   ts-node src/admin_list_vaults.ts 2 "Zaga"
  //
  // argv[2] = workspace: '2' for secondary ('' for primary)
  // argv[3] = optional filter substring (client_id, name, or id)
  const ws = (process.argv[2] || '2') as '' | '2';
  const filter = (process.argv[3] || '').toLowerCase();

  const fb = makeFireblocksClient(ws);
  if (!fb.enabled) {
    console.error(`Fireblocks${ws || ' (primary)'} env not set/enabled.`);
    process.exit(1);
  }

  let next: string | undefined = undefined;
  let total = 0;

  do {
    const page = await fb.listVaultAccounts(200, next);
    const accounts = page?.accounts || [];
    for (const a of accounts) {
      const id = String(a.id ?? a.vaultAccountId ?? '');
      const name = String(a.name ?? a.accountName ?? '');
      const line = `${id}\t${name}`;
      if (!filter || line.toLowerCase().includes(filter)) {
        console.log(line);
      }
    }
    total += accounts.length;
    next = page?.next;
  } while (next);

  console.error(`Listed ${total} accounts from workspace '${ws || 'primary'}'.`);
}

main().catch((e) => {
  console.error(e?.response?.data || e);
  process.exit(1);
});
