import 'dotenv/config';
import express from 'express';
import { bot } from './bot';
import { ensureSchema } from './db';

const app = express();

// Verify Telegram secret header for webhook requests
app.use('/telegram/webhook', (req, res, next) => {
  const expected = process.env.WEBHOOK_SECRET_TOKEN;
  const got = req.header('X-Telegram-Bot-Api-Secret-Token');
  if (!expected || got === expected) return next();
  res.status(403).send('forbidden');
});

app.use(express.json());

// Telegraf webhook handler
app.post('/telegram/webhook', (bot.webhookCallback('/telegram/webhook') as any));

// Health probe
app.get('/health', (_req, res) => res.send('ok'));

const port = Number(process.env.PORT) || 8080;

(async () => {
  await ensureSchema();
  app.listen(port, () => {
    console.log('listening on', port);
  });
})();
