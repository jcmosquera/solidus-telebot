import Decimal from 'decimal.js';

export type Holding = { assetId:string, qty:string, coingeckoId:string };
export type Valued = { assetId:string, qty:string, price:number, value:string, pnlUsd:string, pnlPct:string };

export async function valueHoldings(
  items: Holding[],
  fetchNow: (ids:string[])=>Promise<Record<string,number>>,
  fetch24: (id:string)=>Promise<number>
): Promise<{ lines:Valued[], totalUsd:string, totalPnlUsd:string }> {
  const ids = Array.from(new Set(items.map(i => i.coingeckoId)));
  const now = await fetchNow(ids);

  let total = new Decimal(0);
  let totalPnl = new Decimal(0);
  const lines: Valued[] = [];

  for (const h of items) {
    const qty = new Decimal(h.qty || '0');
    if (qty.isZero()) continue;

    const p0 = new Decimal(now[h.coingeckoId] || 0);
    const p1 = new Decimal(await fetch24(h.coingeckoId));
    const val = qty.mul(p0);
    const pnlUsd = qty.mul(p0.minus(p1));
    const pnlPct = p1.gt(0) ? p0.minus(p1).div(p1).mul(100) : new Decimal(0);

    total = total.plus(val);
    totalPnl = totalPnl.plus(pnlUsd);

    lines.push({
      assetId: h.assetId,
      qty: qty.toFixed(8),
      price: p0.toNumber(),
      value: val.toFixed(2),
      pnlUsd: pnlUsd.toFixed(2),
      pnlPct: pnlPct.toFixed(2)
    });
  }

  return { lines, totalUsd: total.toFixed(2), totalPnlUsd: totalPnl.toFixed(2) };
}
