# SAT Math Lectures – Static Site

This repo contains Markdown lectures in `blogs/` and a generated static site in `site/`.

## Quick start
- Open `site/index.html` in your browser to view the site.

## GitHub Pages deploy
This repo is pre-configured to deploy the `site/` folder to GitHub Pages using Actions.

Steps:
- Make sure your default branch is `main` and push this repo to GitHub.
- In GitHub: Settings → Pages → Source = “GitHub Actions”.
- Push changes to `site/` and GitHub Actions will publish automatically.

The workflow lives at `.github/workflows/pages.yml` and uploads `site/` as the Pages artifact.
