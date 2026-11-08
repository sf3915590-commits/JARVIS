from datetime import datetime, timezone
from ddgs import DDGS


FRESH_KEYWORDS = {
    "latest",
    "current",
    "today",
    "recent",
    "news",
    "now",
    "currently",
    "net worth",
    "price",
    "stock price",
    "market cap",
}


def is_fresh_query(text):
    t = text.lower()
    return any(keyword in t for keyword in FRESH_KEYWORDS)


def search_web(query, max_results=5):
    try:
        results = list(
            DDGS().news(
                query,
                max_results=max_results,
            )
        )

        clean = []

        for item in results:
            clean.append({
                "title": item.get("title", ""),
                "url": item.get("url", item.get("href", "")),
                "snippet": item.get("body", ""),
                "date": item.get("date"),
            })

        return clean

    except Exception as error:
        print(f"[Web] Search failed: {error}", flush=True)
        return []


def format_results(results):
    if not results:
        return "No fresh web results were found."

    lines = []

    for i, result in enumerate(results, 1):
        lines.append(
            f"[{i}] {result['title']}\n"
            f"Source: {result['url']}\n"
            f"Date: {result['date'] or 'Date not provided'}\n"
            f"Snippet: {result['snippet']}"
        )

    return "\n\n".join(lines)

