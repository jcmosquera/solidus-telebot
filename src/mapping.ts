export const DEFAULT_ASSET_MAP: Record<string,string> = {
  BTC: 'bitcoin',
  ETH: 'ethereum',
  USDC: 'usd-coin',
  USDT: 'tether'
};

export function mapAssetId(assetId: string, overrides?: Record<string,string>) {
  const key = assetId.toUpperCase();
  return overrides?.[key] ?? DEFAULT_ASSET_MAP[key] ?? null;
}
