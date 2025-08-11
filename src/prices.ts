import axios from 'axios';

type PriceNow = Record<string,{ usd:number }>;
const http = axios.create({ baseURL: 'https://api.coingecko.com/api/v3', timeout: 20000 });

const memNow: Record<string,{usd:number, at:number}> = {};
const mem24: Record<string,{usd:number, at:number}> = {};

export async function getCurrentPrices(ids: string[]) {
  const need = ids.filter(id => !(id in memNow) || (Date.now()-memNow[id].at)>60_000);
  if (need.length) {
    const url = `/simple/price?ids=${encodeURIComponent(need.join(','))}&vs_currencies=usd`;
    const { data } = await http.get<PriceNow>(url);
    for (const id of Object.keys(data)) {
      memNow[id] = { usd: data[id].usd, at: Date.now() };
    }
  }
  const out: Record<string,number> = {};
  for (const id of ids) out[id] = memNow[id]?.usd ?? 0;
  return out;
}

export async function getPrice24hAgo(id: string) {
  if (mem24[id] && (Date.now() - mem24[id].at) < 5*60_000) return mem24[id].usd;
  const url = `/coins/${encodeURIComponent(id)}/market_chart?vs_currency=usd&days=1&interval=minute`;
  const { data } = await http.get(url);
  const prices: [number, number][] = data.prices;
  const first = prices?.[0]?.[1];
  const last  = prices?.[prices.length-1]?.[1];
  const p24 = typeof first === 'number' ? first : last;
  mem24[id] = { usd: p24, at: Date.now() };
  return p24;
}
