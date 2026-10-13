# HairWorks-Community

Shared hair edits for the Witcher 3 HairWorks mod, made with Groom Studio. Browsing needs no login.

## How to share
1. In Groom Studio open the Community tab and log in with GitHub (device flow).
2. Press Publish. Studio forks this repo, commits your pack folder and opens a pull request.
3. CI validates the pack; a maintainer merges. Set `status` to `wip` while iterating and `ready` when done.

## Rules
- Edit ops only: no game files, no NVIDIA SDK material (no .w2mesh/.w2ent/.bundle/.apb/.dll/.lib, no GFSDK/HairWorks SDK headers).
- One folder per author: `characters/<char>/<slot>/<githubuser>__<pack>/` containing `pack.json`, `edits.hwgroom`, optional `preview.png` (<= 300 KB). Pack folder <= 2 MB.
- A PR may only touch folders whose name starts with your own GitHub user name + `__`.
- Fork a pack by copying it into your own folder and setting `based_on` in `pack.json` (`<user>__<pack>@<sha>`).
- Licensed CC-BY-4.0 (see LICENSE.md); the author stays credited.

## Review and safety

- Every change comes as a pull request (GitHub account required). Direct pushes to `main` / `testing` are blocked.
- CI checks each PR with the validator and schemas of the base branch, never the ones in the PR. A PR may only add or change files inside its author's own `characters/<char>/<slot>/<githubuser>__<pack>/` folders, and only `pack.json`, `edits.hwgroom`, `ribbons.json`, `preview.jpg` / `preview.png`.
- A maintainer reviews and merges. After the merge CI publishes the index (`main.json` / `testing.json` on the `index` branch) with the commit and the SHA-256 of every file. The Studio downloads only those files from that commit and checks each hash, then validates the pack again on your PC.
- Packs are data (strand edits and a picture). Nothing in a pack is ever run.
