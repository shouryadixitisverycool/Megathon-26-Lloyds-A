# Repository sync

`IIIT-ECell/megathon26-chuds` is the source. The `sync-personal.yml`
workflow copies all branches and tags to
`shouryadixitisverycool/Megathon-26-Lloyds-A`.

The workflow runs on pushes, on a five-minute schedule, and through
**Run workflow** in GitHub Actions. GitHub may delay scheduled runs.
The schedule covers branches that do not contain the workflow yet.
The repository condition prevents the copied workflow from running in personal.

Authentication uses the source repository's `PERSONAL_SYNC_SSH_KEY` Actions
secret and the destination's write-enabled `Origin automatic sync` deploy key.

Pushes are atomic and never forced. Divergent branches or changed existing tags
fail the run. Personal-only branches and tags are preserved, including refs
deleted in origin. This copies Git history, not issues, releases, or settings.

The deploy key was created with a GitHub CLI OAuth token without `workflow`
scope. GitHub rejects pushes that add or change `.github/workflows` files through
this key. The initial workflow was copied using the maintainer's SSH access.
For future workflow changes, push those commits to personal using maintainer SSH
access, then rerun the failed sync. To remove that restriction, recreate the
deploy key through GitHub's web settings or a token with `repo` and `workflow`
scopes, and replace `PERSONAL_SYNC_SSH_KEY` with the matching private key.
