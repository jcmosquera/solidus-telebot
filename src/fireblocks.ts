import axios from 'axios';
import { SignJWT, importPKCS8 } from 'jose';
import { v4 as uuidv4 } from 'uuid';
import { createHash, createPrivateKey } from 'crypto';

function normalizeBase(raw?: string) {
  return (raw || 'https://api.fireblocks.io')
    .replace(/\/+$/, '')   // strip trailing slashes
    .replace(/\/v1$/, ''); // strip a trailing /v1 if present
}

// Resolve a PEM for a given workspace prefix: '' (primary) or '2' (secondary)
function resolvePrivateKeyPEM(prefix: '' | '2' = ''): string {
  const b64 =
    (process.env[`FIREBLOCKS${prefix}_PRIVATE_KEY_BASE64` as any] as string | undefined) ||
    (process.env.FIREBLOCKS_PRIVATE_KEY_BASE64 as string | undefined);
  if (b64) return Buffer.from(b64, 'base64').toString('utf8');

  let pem =
    (process.env[`FIREBLOCKS${prefix}_PRIVATE_KEY_PEM` as any] as string | undefined) ||
    (process.env.FIREBLOCKS_PRIVATE_KEY_PEM as string | undefined) ||
    '';
  if (pem.includes('\\n')) pem = pem.replace(/\\n/g, '\n');
  return pem.trim();
}

// Support PKCS#1 and PKCS#8
async function importPrivateKey(prefix: '' | '2' = '') {
  const pem = resolvePrivateKeyPEM(prefix);
  if (!pem) throw new Error(`Missing Fireblocks${prefix} private key env`);
  if (pem.includes('BEGIN RSA PRIVATE KEY')) {
    const keyObj = createPrivateKey({ key: pem, format: 'pem' });
    const pkcs8Pem = keyObj.export({ type: 'pkcs8', format: 'pem' }).toString();
    return importPKCS8(pkcs8Pem, 'RS256');
  }
  return importPKCS8(pem, 'RS256');
}

async function signJwt(
  prefix: '' | '2',
  uri: string,
  method: 'GET' | 'POST' | 'DELETE' = 'GET',
  body?: string
) {
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + 55;
  const nonce = uuidv4();

  const apiKey =
    (process.env[`FIREBLOCKS${prefix}_API_KEY` as any] as string | undefined) ||
    (process.env.FIREBLOCKS_API_KEY as string | undefined);
  const payload: any = { uri, nonce, iat, exp, sub: apiKey };
  if (method !== 'GET' && body) {
    const bodyHash = createHash('sha256').update(body, 'utf8').digest('hex');
    payload.bodyHash = bodyHash;
  }

  const key = await importPrivateKey(prefix);
  return new SignJWT(payload).setProtectedHeader({ alg: 'RS256' }).sign(key);
}

// Factory for a Fireblocks client bound to a workspace
export function makeFireblocksClient(prefix: '' | '2' = '') {
  const base = normalizeBase(
    ((process.env[`FIREBLOCKS${prefix}_BASE_URL` as any] as string | undefined) ||
      (process.env.FIREBLOCKS_BASE_URL as string | undefined)) ?? 'https://api.fireblocks.io'
  );
  const apiKey =
    (process.env[`FIREBLOCKS${prefix}_API_KEY` as any] as string | undefined) ||
    (process.env.FIREBLOCKS_API_KEY as string | undefined);
  const pem = resolvePrivateKeyPEM(prefix);

  const http = axios.create({ baseURL: base, timeout: 15000 });
  const enabled = Boolean(apiKey && pem);

  return {
    enabled,

    // GET /v1/vault/accounts/{id}
    async getVaultAccount(vaultAccountId: string) {
      const path = `/v1/vault/accounts/${vaultAccountId}`;
      const token = await signJwt(prefix, path, 'GET');
      const { data } = await http.get(path, {
        headers: { 'X-API-Key': apiKey, Authorization: `Bearer ${token}` },
      });
      return data; // includes .assets[]
    },

    // GET /v1/vault/accounts_paged?limit=...&next=...
    async listVaultAccounts(limit = 200, next?: string) {
      const qs = new URLSearchParams({ limit: String(limit) });
      if (next) qs.set('next', next);
      const path = `/v1/vault/accounts_paged?${qs.toString()}`;
      const token = await signJwt(prefix, path, 'GET');
      const { data } = await http.get(path, {
        headers: { 'X-API-Key': apiKey, Authorization: `Bearer ${token}` },
      });
      return data as { accounts: any[]; next?: string }; // returns { accounts, next? }
    },
  };
}
