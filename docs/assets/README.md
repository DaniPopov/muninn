# docs/assets

Images used in the README and the docs: logo, diagrams, screenshots.

Reference them with a relative path, for example from the root README:
`![Muninn](docs/assets/logo-lockup.png)`

| File | Size | Use |
|---|---|---|
| `readme-banner.png` | 1280 x 400 | top of the root README |
| `logo-lockup.png` | 1920 x 1080 | GitHub social preview, slides, announcements |
| `muninn-mascot.png` | 512 x 512 | README illustration, stickers |
| `muninn-icon.png` | 512 x 512 | avatar: GitHub org, WhatsApp profile picture, favicon source |

File names are lowercase kebab-case, with no spaces or `@`, so Markdown links don't break.

Images used inside the web app go in `apps/dashboard/src/assets/` instead.
See [docs/architecture/dashboard.md](../architecture/dashboard.md#images-and-other-assets).
