import { Telegraf } from 'telegraf';
import { query } from './db';
import { mapAssetId } from './mapping';
import { getVaultAccount } from './fireblocks';
import { getCurrentPrices, getPrice24hAgo } from './prices';
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
    // Resolve client mapping
    const links = await query<{client_id:string}>("select client_id from user_links where telegram_user_id=$1", [ctx.from.id]);
    const link = links[0];
    if (!link) return ctx.reply("Not linked. Use /link YOURCODE first.");

    const c = await query<{vault_account_id:string, client_name:string}>(
      "select vault_account_id, client_name from clients where client_id=$1",
      [link.client_id]
    );
    if (!c[0]) return ctx.reply("No vault mapped. Contact support.");

    // Fireblocks balances
    const vault = await getVaultAccount(c[0].vault_account_id);
    const assets: any[] = (vault.assets || []);

    // Optional overrides from DB
    const overridesRows = await query<{asset_id:string, coingecko_id:string}>("select asset_id, coingecko_id from asset_map");
    const overrides = Object.fromEntries(overridesRows.map(r => [r.asset_id.toUpperCase(), r.coingecko_id]));

    const holdings = assets
      .map(a => ({ assetId: a.id, qty: a.total, coingeckoId: mapAssetId(a.id, overrides) }))
      .filter(h => h.coingeckoId);

    if (!holdings.length) {
      await query("insert into audit(telegram_user_id, client_id, action) values($1,$2,'portfolio_empty')",
        [ctx.from.id, link.client_id]);
      return ctx.reply(`${c[0].client_name}: no balances found.`);
    }

    const { lines, totalUsd, totalPnlUsd } = await valueHoldings(holdings, getCurrentPrices, getPrice24hAgo);

    let msg = `Client: ${c[0].client_name}\nVault: ${c[0].vault_account_id}\n\nHoldings:\n`;
    for (const l of lines) {
      const value = Number(l.value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      const pnlUsd = Number(l.pnlUsd).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      msg += `${l.assetId}  ${l.qty}   $${value}  (24h: $${pnlUsd} / ${l.pnlPct}%)\n`;
    }
    const tVal = Number(totalUsd).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const tPnl = Number(totalPnlUsd).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    msg += `\nTotal: $${tVal}   24h P&L: $${tPnl}`;

    await query("insert into audit(telegram_user_id, client_id, action) values($1,$2,'portfolio')",
      [ctx.from.id, link.client_id]);
    await ctx.reply(msg);
  } catch (e:any) {
    console.error(e?.response?.data || e);
    await ctx.reply("Sorry, something went wrong fetching your portfolio. Please try again later.");
  }
});
