import { Telegraf } from 'telegraf';
import { query } from './db';
import { mapAssetId } from './mapping';
import { getCurrentPrices, getPrice24hAgo } from './prices';
import { makeFireblocksClient } from './fireblocks';
import Decimal from 'decimal.js';
import { valueHoldings } from './portfolio';

const BOT_TOKEN = process.env.BOT_TOKEN!;
export const bot = new Telegraf(BOT_TOKEN);

// /start
bot.start(async (ctx) => {
  await ctx.reply(
    "Welcome! If you’re a Solidus client, link your account with:\n/link YOURCODE"
  );
});

// /link CODE
bot.command('link', async (ctx) => {
  const parts = ctx.message?.text?.split(' ') ?? [];
  const code = parts.slice(1).join(' ').trim();
  if (!code) return ctx.reply("Usage: /link YOURCODE");

  const crypto = await import('crypto');
  const hash = crypto.createHash('sha256').update(code).digest('hex');

  const rows = await query<{client_id:string, expires_at:string, used_at:string}>(
    "select client_id, expires_at, used_at from link_codes where code_hash=$1",
    [hash]
  );
  const row = rows[0];
  if (!row) return ctx.reply("Invalid code.");
  if (row.used_at) return ctx.reply("This code was already used.");
  if (new Date(row.expires_at) < new Date()) return ctx.reply("This code expired.");

  await query("insert into user_links(telegram_user_id, client_id) values($1,$2) on conflict (telegram_user_id) do update set client_id=excluded.client_id",
    [ctx.from.id, row.client_id]);
  await query("update link_codes set used_at=now() where code_hash=$1", [hash]);
  await query("insert into audit(telegram_user_id, client_id, action) values($1,$2,'link')", [ctx.from.id, row.client_id]);

  await ctx.reply("Linked! You can now use /portfolio");
});

// /portfolio
bot.command('portfolio', async (ctx) => {
  try {
    // 1) Resolve which client this Telegram user is linked to
    const links = await query<{ client_id: string }>(
      "select client_id from user_links where telegram_user_id=$1",
      [ctx.from.id]
    );
    const link = links[0];
    if (!link) return ctx.reply("Not linked. Use /link YOURCODE first.");

    // 2) Display name
    const cinfo = await query<{ client_name: string }>(
      "select client_name from clients where client_id=$1",
      [link.client_id]
    );
    const clientName = cinfo[0]?.client_name || 'Your Account';

    // 3) All mapped vaults (primary + secondary)
    const vaultRows = await query<{ workspace: string; vault_account_id: string }>(
      "select workspace, vault_account_id from client_vaults where client_id=$1",
      [link.client_id]
    );
    // Backward compatibility: if none, fallback to legacy clients table
    if (!vaultRows.length) {
      const legacy = await query<{ vault_account_id: string }>(
        "select vault_account_id from clients where client_id=$1",
        [link.client_id]
      );
      if (legacy[0]?.vault_account_id) {
        vaultRows.push({ workspace: 'primary', vault_account_id: legacy[0].vault_account_id });
      }
    }
    if (!vaultRows.length) {
      await query(
        "insert into audit(telegram_user_id, client_id, action) values($1,$2,'portfolio_empty')",
        [ctx.from.id, link.client_id]
      );
      return ctx.reply(`No balances found for your account.`);
    }

    // 4) Fireblocks clients (primary + secondary)
    const { makeFireblocksClient } = await import('./fireblocks');
    const fb1 = makeFireblocksClient('');  // primary
    const fb2 = makeFireblocksClient('2'); // secondary

    // 5) Fetch assets across all vaults
    type FBAsset = { id: string; total: string };
    let allAssets: FBAsset[] = [];
    for (const v of vaultRows) {
      try {
        if (v.workspace === 'primary' && fb1.enabled) {
          const data = await fb1.getVaultAccount(v.vault_account_id);
          allAssets = allAssets.concat((data.assets || []) as FBAsset[]);
        } else if (v.workspace === 'secondary' && fb2.enabled) {
          const data = await fb2.getVaultAccount(v.vault_account_id);
          allAssets = allAssets.concat((data.assets || []) as FBAsset[]);
        }
      } catch (e) {
        console.error(`Failed to fetch ${v.workspace} vault ${v.vault_account_id}`, e);
      }
    }
    if (!allAssets.length) {
      await query(
        "insert into audit(telegram_user_id, client_id, action) values($1,$2,'portfolio_empty')",
        [ctx.from.id, link.client_id]
      );
      return ctx.reply(`No balances found for your account.`);
    }

    // 6) Aggregate by assetId
    const { default: Decimal } = await import('decimal.js');
    const totals = new Map<string, any>();
    for (const a of allAssets) {
      const id = (a.id || '').toUpperCase();
      if (!id) continue;
      const prev = totals.get(id) || new Decimal(0);
      totals.set(id, prev.plus(new Decimal(a.total || '0')));
    }

    // 7) Map assets to CoinGecko IDs (overrides from DB)
    const overridesRows = await query<{ asset_id: string; coingecko_id: string }>(
      "select asset_id, coingecko_id from asset_map"
    );
    const overrides = Object.fromEntries(overridesRows.map((r) => [r.asset_id.toUpperCase(), r.coingecko_id]));
    const { mapAssetId } = await import('./mapping');

    const holdings = Array.from(totals.entries())
      .map(([assetId, qty]) => ({ assetId, qty: qty.toFixed(8), coingeckoId: mapAssetId(assetId, overrides) }))
      .filter((h) => h.coingeckoId);

    if (!holdings.length) {
      await query(
        "insert into audit(telegram_user_id, client_id, action) values($1,$2,'portfolio_empty')",
        [ctx.from.id, link.client_id]
      );
      return ctx.reply(`${clientName}: no balances found.`);
    }

    // 8) Value and format output
    const { valueHoldings } = await import('./portfolio');
    const { getCurrentPrices, getPrice24hAgo } = await import('./prices');
    const { lines, totalUsd, totalPnlUsd } = await valueHoldings(
      holdings,
      getCurrentPrices,
      getPrice24hAgo
    );

    const sign = (n: number) => (n > 0 ? '+' : n < 0 ? '−' : '');
    const fmt2 = (x: string | number) =>
      Number(x).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    let msg = `Client: ${clientName}\n`;
    msg += `\nCurrent Balance:\n`; // label change & no Vault line
    for (const l of lines) {
      const value = fmt2(l.value);
      const pnlNum = Number(l.pnlUsd);
      const pnlUsd = fmt2(pnlNum);
      msg += `${l.assetId}  ${l.qty}   $${value}  (24h: ${sign(pnlNum)}$${pnlUsd} / ${l.pnlPct}%)\n`;
    }
    const tVal = fmt2(totalUsd);
    const tPnl = Number(totalPnlUsd);
    msg += `\nTotal: $${tVal}   24h P&L: ${sign(tPnl)}$${fmt2(tPnl)}`;

    await query("insert into audit(telegram_user_id, client_id, action) values($1,$2,'portfolio')", [
      ctx.from.id,
      link.client_id,
    ]);
    await ctx.reply(msg);
  } catch (e: any) {
    console.error(e);
    await ctx.reply('Sorry, something went wrong fetching your portfolio. Please try again later.');
  }
});
