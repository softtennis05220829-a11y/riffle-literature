# RIFFLE — River Literature Radar

A Japanese, mobile-friendly academic paper reading desk for river ecology, Ayu grazing, periphyton, stream biofilms, nutrients, isotope ecology and flood recovery.

**Site layout**: Daily AM foundation + PM recent/trending paper, full individual paper pages, take-home message first, search, tags, local bookmarks, DOI links, research context and caveats.

## Run locally (no sign-in / no API key needed)

The `dist/` directory is a complete ready-built static website with 9 reviewed literature notes. Open `dist/index.html` in a browser, or serve it on your computer:

```bash
cd river-literature-radar
python3 -m http.server 8000 --directory dist
# Visit http://localhost:8000
```

All CSS and JS work locally. Bookmarks live only in the current browser's local storage (not synced across devices).

## Publish to a real website: GitHub Pages

1. Create a GitHub repository (for example `riffle-literature`). Upload **all source files and folders** from this folder (including `.github/` and `scripts/`). Use `main` as the default branch.
2. In **Settings → Pages → Build and deployment**, choose **Source: GitHub Actions**.
3. In **Actions → Build and publish RIFFLE → Run workflow**, run it once. The public URL is listed in the workflow's deployment result (typically `https://YOUR_USERNAME.github.io/riffle-literature/`).
4. For *newly published papers with AI-generated Japanese notes*, add a GitHub repository secret `OPENAI_API_KEY` under **Settings → Secrets and variables → Actions**. The API key incurs usage costs independent of ChatGPT subscriptions. Optionally add `OPENALEX_API_KEY` (a free OpenAlex key is useful for rate limits).

**Automatic schedules (Japan time)**:

- 07:00 JST each day: one classic/foundational paper, rotated from a verified shortlist.
- 18:00 JST each day: one recent/trending paper discovered through OpenAlex and summarized using OpenAI **if `OPENAI_API_KEY` is configured**. Without it, the site rotates a curated verified selection of 2025–2026 papers instead of inventing summaries.

GitHub Actions cron is **best-effort, not to-the-minute**; workloads can delay or skip a scheduled execution. New summaries depend on API availability and costs. If retrieval/generation fails, the previous/curated content remains usable.

## How the daily digest works

`scripts/build.py` reads `data/curated.json`, `data/generated.json`, `data/archive.json` and generates `dist/index.html` plus one `dist/papers/ID.html` per paper. Every run rebuilds a static web app—**no secret key appears in the HTML or JavaScript**.

For an evening refresh it queries [OpenAlex](https://openalex.org/) for recent peer-reviewed *article* metadata and reconstructed abstracts, scores for stream ecology relevance and deduplicates by DOI. If OpenAI is configured, it generates Japanese structured notes based on **the abstract only**, with strict instructions not to hallucinate methods, quantitative findings or causality. Such notes are marked `AI生成要約（本文未照合）`.

This is not a substitute for peer review of the AI summaries. Always read original articles, particularly before citing them in a thesis. Automatic novelty assessments are relative interpretations of abstracts—not globally validated priority claims. The initial hand-curated collection was checked against publisher/PubMed abstracts or accessible original papers.

### Maintenance / customization

- To add a fully checked paper: add a unique entry to `data/curated.json` using the same keys, or edit a copy of an existing record. Keep `id` URL-safe (`[a-z0-9-]`) and `doi` unique.
- To adjust research keywords: change `queries` and relevance keywords in `discover_openalex` within `scripts/build.py`.
- To change the update times: edit both UTC cron expressions in `.github/workflows/publish.yml`. Japan has no daylight savings time.
- To rebuild without external API usage: `python3 scripts/build.py`.
- To test an API-backed evening run: `OPENAI_API_KEY=... python3 scripts/build.py --refresh --slot evening`. Do not place keys directly in files or commit them.

### Why not scrape full papers?

Automated notes rely on source abstracts and metadata, not unauthorized extraction of paywalled PDFs. Links go to the original DOI or source. This respects copyright and helps prevent misleading unsupported detail. Abstract-only auto notes intentionally label limitations; for a thesis-level citation check, inspect the original full paper.

## Limitations

- GitHub Pages hosting and GitHub Actions are not activated by downloading this ZIP: **the user must publish the repository**.
- Without `OPENAI_API_KEY`, automatic discovery of new papers is disabled; it still rotates researched recent papers and legacy papers.
- No native push/email notifications are included. The site itself updates on schedule once hosted, and can be bookmarked.
- This website is a research aid, not a bibliographic database or a fully validated systematic review.

## Source docs

- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- OpenAlex API: https://help.openalex.org/api/
- OpenAI Responses API: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
