"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in week 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def _cap(pieces: list[str]) -> list[str]:
    """Split any piece over CHUNK_SIZE at the nearest sentence end."""
    out: list[str] = []
    for piece in pieces:
        while len(piece) > config.CHUNK_SIZE:
            cut = piece.rfind(". ", 0, config.CHUNK_SIZE)
            if cut == -1:
                break
            out.append(piece[: cut + 1].strip())
            piece = piece[cut + 2 :].strip()
        out.append(piece)
    return out


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split each document into paragraph-sized chunks, titled.

    Every document in campus_life is a title line followed by one to four short
    paragraphs, so paragraphs are the natural seam — a fixed character window
    either cuts nothing (at 800) or slices off fragments (at 500). Short
    paragraphs merge forward so nothing stands alone that can't answer a
    question, and the title is repeated on every chunk so "$1.50" stays
    attached to "Old Brewhouse".
    """
    chunks: list[Chunk] = []
    for doc in documents:
        paragraphs = [p.strip() for p in doc.text.split("\n\n") if p.strip()]
        if not paragraphs:
            continue

        title = paragraphs[0]
        body = paragraphs[1:]

        # Merge paragraphs forward until each piece carries enough to stand
        # alone. "The good: ..." on its own is 80 characters and answers
        # nothing; joined to "The bad: ..." it's a usable thought.
        pieces: list[str] = []
        buffer = ""
        for para in body:
            buffer = f"{buffer}\n\n{para}" if buffer else para
            if len(buffer) >= config.MIN_CHUNK_CHARS:
                pieces.append(buffer)
                buffer = ""

        # Whatever is left over is too short to be its own chunk, so it joins
        # the previous one rather than becoming a fragment.
        if buffer:
            if pieces:
                pieces[-1] = f"{pieces[-1]}\n\n{buffer}"
            else:
                pieces.append(buffer)

        if not pieces:
            pieces = [title]

        for index, piece in enumerate(_cap(pieces)):
            chunks.append(
                Chunk(
                    text=f"{title}\n\n{piece}",
                    source=doc.source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
