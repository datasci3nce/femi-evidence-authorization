# Publish this source release to GitHub

The ZIP contains the files for the repository, not a public GitHub URL. Publishing requires an authenticated GitHub session and a destination repository. **Never upload `FEMI_Research_Private_Evidence_20261109.zip`.**

1. On GitHub, create an **empty** public repository, e.g. `femi-evidence-authorization` (do not initialize a README, license or .gitignore).
2. Extract `FEMI_GITHUB_READY_20261109.zip`, and open a terminal inside `FEMI-GitHub-Release/`.
3. Run:

```bash
python tools/verify_release.py
git init -b main
git add .
git commit -m "Release FEMI reproducibility archive and paper"
git remote add origin https://github.com/YOUR_USERNAME/femi-evidence-authorization.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub account and authenticate when prompted. If an existing repository is used, review its files/branch before pushing.

4. Once uploaded, add the public repository URL to Apart's submission form, if desired. The report PDF must still be submitted separately via the official form.

**Note:** Releasing this source code does not imply a new software license. Contact the author before adding a license or distributing third-party benchmark text.
