# celeb-couple

Private repository. The project has not started yet — this commit is the
scaffold only.

## Working on this repo

Several agents work here at once, one per checkout, under the checkout layout
and git protocol in [AGENTS.md](AGENTS.md). Read that file first.

Checkouts live in `~/Code/misc/celebrity-couple/` as `repo-0` … `repo-3`. The
container directory is not itself a checkout.

## Adding a checkout

```sh
git -C ~/Code/misc/celebrity-couple clone git@github.com:tonygwu/celeb-couple.git repo-4
git -C ~/Code/misc/celebrity-couple/repo-4 config user.email 446441+tonygwu@users.noreply.github.com
```

Then add its row to the checkout table in `AGENTS.md` and push that change.
