# Shadow Run cloud worker

The game no longer has any multiplayer modes (Tag Duels, Draft Duels and Ultimate Collector were removed).
This Cloudflare Worker now only provides two optional, non-multiplayer services:

* `/backup/*` – encrypted-by-the-client device backups (`backup.mjs`)
* `/progress/*` – cross-device progress sync (`progress.mjs`)

The public endpoint is configured in `android/web/multiplayer-config.json` (the file name is historical; it is
only read by `device-sync.js` and `device-backup.js`).

## Deploying

Run `wrangler deploy` from this folder. Migration `v7` **deletes** the retired Durable Object classes
(`RoomRegistry`, `GameRelay`, `CollectorRegistry`, `DraftRegistry`) together with any rooms, Collector decks and
draft data stored in them. Back up anything you want to keep before the first deploy.

Tests: `npm test` (progress and backup only).
