# Source ingestion: first implementation

The ingestion module fetches **real observations** from official APIs and stores them in a local SQLite `observations` table. No data is fabricated. It does not yet classify or score problems.

## YouTube

Enable YouTube Data API v3 in a Google Cloud project and obtain an API key. Set `YOUTUBE_API_KEY` in your shell, then run:

```bash
python ingestion.py youtube --video-id VIDEO_ID --limit 100
```

Fetches top-level comments using `commentThreads.list`. Replies, videos with disabled comments, API quotas and restricted content are not handled.

## Reddit

Obtain authorized Reddit OAuth API access and a bearer token consistent with Reddit's developer policies. Set `REDDIT_ACCESS_TOKEN` and a descriptive `REDDIT_USER_AGENT`, then run:

```bash
python ingestion.py reddit --subreddit productivity --limit 100
```

Fetches newest posts using the OAuth listing endpoint. Token refresh, Reddit approval requirements and rate-limit retries are not implemented. Do not bypass restrictions or use unauthorized scraping.

## Data handling

- Stored fields: platform, external ID, URL, text, publication time, context and collection time.
- Unique (platform, external ID) prevents repeated ingestion of the same observation.
- Credentials are read from environment variables and should never be committed.
- `research.sqlite3` is ignored by Git.
- No automatic country inference, personal data removal, AI classification or opportunity ranking yet.
- Before production, add retention/deletion policy, request throttling, privacy review and source-specific compliance.
