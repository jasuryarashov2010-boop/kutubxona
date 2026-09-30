# 📚 Kitobxon WOW V3

Telegram bot for a literature/book recommendation channel.

## UI principles
- User/Admin navigation uses persistent Reply Keyboard.
- Record-specific actions (publish, reject, edit, support reply) use Inline Keyboard.
- User prompt messages are replaced step-by-step so the form stays visually clean.
- Channel posts use consistent HTML formatting, emoji hierarchy, quote blocks, and separators.

## Core flow
1. `/start` → mandatory subscription gate (admins bypass it)
2. 📖 Book recommendation → title → author → review → optional photo
3. 👀 Preview → edit/send/cancel
4. Admin receives moderation card
5. ✅ Publish → post goes to configured target channel
6. New target-channel posts automatically receive the configured emoji reaction

## Admin
- 📥 Recommendations
- 📨 Support tickets + replies
- 📣 Broadcast with preview + throttling
- 🎨 Post design
- 🔥 Reaction settings (admin writes emoji)
- 📢 Target/subscription channel settings
- 👥 Search + block/unblock users
- 📊 Stats
- ⚙️ System status + stale publishing recovery

## Render
Build:
`pip install -r requirements.txt`

Start:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health:
`/health`

Set:
- `PYTHON_VERSION=3.13.5`
- `BOT_TOKEN`
- `ADMIN_IDS=ID1,ID2`
- `BOT_USERNAME`
- `DATABASE_URL` and `REDIS_URL` from Render resources

Target and subscription channels are configured by admins inside the bot, so a missing channel ID cannot prevent the service from booting.

## Telegram permissions
- Bot must be admin in the target channel to publish and receive channel post updates.
- Bot must be able to check membership in the required-subscription channel; for reliable membership checks, make it an admin there.
- For reactions, the configured reaction must be available in that chat.
