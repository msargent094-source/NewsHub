# NewsHub

Mobile-first Australian news aggregator.

## Enable hosting

In **Settings → Pages**, choose **Deploy from a branch**, **main**, **/(root)** and save. Then open **Actions → Refresh news → Run workflow** to populate the first feed.

App URL: https://msargent094-source.github.io/NewsHub/

The background workflow checks Google News RSS search results filtered for ABC News, SBS News, The Guardian Australia, Reuters, BBC News, Al Jazeera, and Associated Press every 15 minutes (GitHub schedules may run late). The app polls the published JSON every 10 minutes. Source discovery is best-effort and may be incomplete. Article links open the publisher via Google News. Preferences and bookmarks remain in local browser storage.
