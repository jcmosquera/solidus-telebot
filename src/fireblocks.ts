import axios from 'axios';
import { SignJWT, importPKCS8, importPKCS1 } from 'jose';
import { v4 as uuidv4 } from 'uuid';

const API_KEY = process.env.FIREBLOCKS_API_KEY!;
const BASE_URL = process.env.FIREBLOCKS_BASE_URL || 'https://api.fireblocks.io/v1';

function resolvePrivateKeyPEM(): string {
  // Priority: BASE64 -> direct PEM -> PEM with \n escapes
  const b64 = process.env.FIREBLOCKS_PRIVATE_KEY_BASE64;
  if (b64) {
    return Buffer.from(b64, 'base64').toString('utf8');
  }
  let pem = process.env.FIREBLOCKS_PRIVATE_KEY_PEM || '';
  if (pem.includes('\\n')) pem = pem.replace(/\\n/g, '\n');
  return pem;
}

async function importPrivateKey() {
  const pem = resolvePrivateKeyPEM().trim();
  if (!pem) throw new Error('Missing Fireblocks private key env');
  if (pem.includes('BEGIN RSA PRIVATE KEY')) {
    return importPKCS1(pem, 'RS256');
  }
  return importPKCS8(pem, 'RS256');
}

async function signJwt(uri: string, method: 'GET'|'POST'|'DELETE'='GET', bodyHash?: string) {
  const iat = Math.floor(Date.now()/1000);
  const exp = iat + 55;
  const nonce = uuidv4();
  const payload: any = { uri, nonce, iat, exp, sub: API_KEY };
  if (method !== 'GET' && bodyHash) payload.bodyHash = bodyHash;

  const key = await importPrivateKey();
  const jwt = await new SignJWT(payload)
    .setProtectedHeader({ alg: 'RS256' })
    .sign(key);
  return jwt;
}

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 15000
});

export async function getVaultAccount(vaultAccountId: string) {
  const path = `/v1/vault/accounts/${vaultAccountId}`;
  const token = await signJwt(path, 'GET');
  const { data } = await http.get(path, {
    headers: {
      'X-API-Key': API_KEY,
      'Authorization': `Bearer ${token}`
    }
  });
  return data; // includes .assets[]
}
