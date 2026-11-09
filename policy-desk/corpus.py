"""Fetch the five public handbook articles and build a reproducible chunk snapshot."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SNAPSHOT = DATA / "chunks.json"
SOURCES = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BLOCKS = {"p", "li", "pre", "tr", "dt", "dd", "blockquote"}
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=1800, chunk_overlap=200)


def chunks_for(html, source, fetched_at):
    key, title, url = source
    soup = BeautifulSoup(html, "html.parser")
    heading = next((h for h in soup.find_all("h1") if h.get_text(" ", strip=True) == title), None)
    if heading is None:
        raise ValueError(f"Expected article title missing at {url}")
    article = heading.find_parent(["article", "main"])
    if article is None:
        article = heading.parent
    sections = []
    trail = [(1, title, "")]
    lines = []
    started = False
    for tag in article.find_all(list(HEADINGS | BLOCKS)):
        if tag is heading:
            started = True
            continue
        if not started or tag.find_parent(["nav", "aside", "footer", "script", "style"]):
            continue
        if tag.name in HEADINGS:
            if tag.name == "h1":
                break
            sections.append((trail, lines))
            level = int(tag.name[1])
            trail = [part for part in trail if part[0] < level]
            label = tag.get_text(" ", strip=True).strip("#¶ ")
            trail.append((level, label, tag.get("id", "")))
            lines = []
        elif not tag.find_parent(list(BLOCKS)):
            if tag.name == "tr":
                line = " | ".join(cell.get_text(" ", strip=True) for cell in tag.find_all(["th", "td"]))
            else:
                line = tag.get_text(" ", strip=True)
            if line and not re.match(r"^(Last modified|View page source|Edit this page)\b", line):
                lines.append(line)
    sections.append((trail, lines))

    result = []
    for trail, lines in sections:
        section = " / ".join(part[1] for part in trail[1:]) or title
        anchor = next((part[2] for part in reversed(trail) if part[2]), "")
        citation_url = f"{url}#{quote(anchor)}" if anchor else url
        for content in SPLITTER.split_text("\n\n".join(lines)):
            identity = hashlib.sha256(f"{key}\n{section}\n{content}".encode()).hexdigest()[:20]
            result.append({
                "id": identity, "content": content,
                "metadata": {"source": key, "title": title, "section": section, "url": citation_url,
                             "fetched_at": fetched_at, "scope": "US" if key == "us-leave" else "global"},
            })
    if not result:
        raise ValueError(f"No article text found at {url}")
    return list({row["id"]: row for row in result}.values())


def refresh():
    now = datetime.now(timezone.utc).isoformat()
    chunks = []
    with httpx.Client(timeout=35, follow_redirects=True) as client:
        for source in SOURCES:
            response = client.get(source[2])
            response.raise_for_status()
            extracted = chunks_for(response.text, source, now)
            chunks.extend(extracted)
            print(f"{source[0]}: {len(extracted)} chunks")
    DATA.mkdir(exist_ok=True)
    temporary = SNAPSHOT.with_suffix(".tmp")
    temporary.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(SNAPSHOT)
    return chunks


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", action="store_true", help="Reuse the local snapshot")
    parser.add_argument("--upload", action="store_true", help="Embed and replace the Supabase snapshot")
    args = parser.parse_args()
    chunks = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if args.snapshot else refresh()
    if args.upload:
        from rag import embed_identity, embeddings, rpc
        model = embeddings()
        if model is None:
            parser.error("Set EMBED_MODEL and EMBED_API_KEY before uploading")
        texts = [f"{row['metadata']['title']} | {row['metadata']['section']}\n{row['content']}" for row in chunks]
        vectors = []
        for offset in range(0, len(texts), 16):
            vectors.extend(model.embed_documents(texts[offset:offset + 16]))
        rows = [
            {**row, "embedding": json.dumps(vector),
             "metadata": {**row["metadata"], "embedding_model": embed_identity()}}
            for row, vector in zip(chunks, vectors, strict=True)
        ]
        print(f"Uploaded {rpc('replace_policy_snapshot', {'chunks': rows})} chunks.")
    else:
        print(f"Local snapshot: {len(chunks)} chunks")


if __name__ == "__main__":
    main()
