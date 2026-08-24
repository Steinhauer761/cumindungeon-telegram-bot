# CumInDungeon Telegram Pre-Signup Bot

Standalone Telegram advertising and pre-signup bot.

## Stack
- Python
- python-telegram-bot 21.10
- Supabase
- Render worker

## Flow
`/start` → 18+ confirmation → name → email → Supabase → personal referral link

## Environment variables
- `TELEGRAM_BOT_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ADMIN_TELEGRAM_ID`

Never commit `.env` or the Supabase service-role key.

## Supabase
Run `supabase.sql` in the Supabase SQL editor.

## Render
Create a Background Worker from this repository.

Build command:
`pip install -r requirements.txt`

Start command:
`python bot.py`

Add the four environment variables in Render.

## Admin
`/stats` returns the number of pre-signups to the configured admin Telegram ID.
