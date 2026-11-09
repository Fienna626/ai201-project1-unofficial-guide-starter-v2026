"""
Stages 3 and 4 of the pipeline: embedding chunks and retrieving them.

Three things in here are worth knowing about, because they'd quietly break the
rest of the project if they were wrong:

1. The Chroma collection is created with cosine distance, explicitly. Chroma
   defaults to squared L2, and the 0.6 threshold the course uses is calibrated
   against cosine. Getting this wrong makes every distance number meaningless.

2. `search` returns the distance alongside each chunk. Milestone 4 has you
   compare distances, so they have to be visible.

3. The embedding model is the one Chroma bundles, not one loaded through
   `sentence-transformers`. It is the same model — `all-MiniLM-L6-v2`, 384
   dimensions — but it arrives as an ONNX build from Chroma's own CDN, so the
   install needs neither PyTorch nor a reachable Hugging Face. See `_embedder`.
"""

import os
import shutil
from dataclasses import dataclass

# Must be set BEFORE chromadb is imported. Without it, some Chroma versions
# print "Failed to send telemetry event ..." on every single call — which looks
# exactly like a real error, isn't one, and cost a previous cohort a lot of
# confused help-channel messages.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb  # noqa: E402

import config
from chunker import Chunk


@dataclass
class Result:
    """One retrieved chunk and how far it was from the question."""

    text: str
    source: str
    label: str
    distance: float   # LOWER IS BETTER. 0.3 is close, 0.9 is unrelated.
    produced_by: str


_model = None

# The model Chroma bundles. Anything else in config.EMBEDDING_MODEL means
# "fetch that one from Hugging Face instead" — see `_embedder`.
BUNDLED_MODEL = "all-MiniLM-L6-v2"


class _OnnxEmbedder:
    """
    Chroma's built-in embedder, wrapped to look like the other two.

    Chroma's embedding functions are called directly and hand back numpy
    arrays. The rest of this file wants `.encode(texts)`, so the adapter lives
    here rather than making every caller care which embedder it got.
    """

    def __init__(self):
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self._ef = ONNXMiniLM_L6_V2()

    def encode(self, texts, show_progress_bar: bool = False):
        return [vector.tolist() for vector in self._ef(list(texts))]


def _sentence_transformer(name: str):
    """
    The escape hatch: any model that isn't the bundled one.

    Week 2's "try a second embedding model" stretch option comes through here,
    and so does anything you set `EMBEDDING_MODEL` to. This path *does* need
    `sentence-transformers` and a reachable Hugging Face, neither of which the
    default install has — which is the whole point of the default install.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            f"config.EMBEDDING_MODEL is set to {name!r}, which isn't the model "
            f"Chroma bundles ({BUNDLED_MODEL!r}), so it has to be downloaded "
            f"from Hugging Face.\n"
            f"Install the optional dependency first:\n"
            f"    pip install 'sentence-transformers>=3.4,<3.5'\n"
            f"Or set EMBEDDING_MODEL back to {BUNDLED_MODEL!r}."
        ) from exc

    return SentenceTransformer(name)


def _embedder():
    """
    Load the embedding model once and keep it.

    First call is slow — it downloads about 80 MB. That's why setup happens
    before class.
    """
    global _model

    if _model is not None:
        return _model

    # Used only by this repo's own smoke test, which runs where no model can be
    # downloaded at all. Never set this yourself.
    if os.getenv("AI201_FAKE_EMBEDDINGS") == "1":
        from _smoke_embedder import FakeEmbedder

        _model = FakeEmbedder()
    elif config.EMBEDDING_MODEL == BUNDLED_MODEL:
        _model = _OnnxEmbedder()
    else:
        _model = _sentence_transformer(config.EMBEDDING_MODEL)

    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Turn text into vectors. Runs on your machine, costs no API quota."""
    vectors = _embedder().encode(texts, show_progress_bar=False)
    # sentence-transformers and the smoke stand-in return something with a
    # .tolist(); _OnnxEmbedder has already done that conversion itself.
    return vectors.tolist() if hasattr(vectors, "tolist") else vectors


def _client():
    return chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_index(
    chunks: list[Chunk],
    corpus: str | None = None,
    variant: str = "default",
) -> int:
    """
    Embed every chunk and store it.

    `variant` lets you keep more than one index of the same corpus at the same
    time. In week 2, when you compare two chunking strategies, index the second
    one as variant="v2" and you can query both instead of deleting the first
    and starting over.
    """
    name = config.collection_name(corpus, variant)
    client = _client()

    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        # ⚠️ Do not remove. Chroma defaults to squared L2, and every distance
        # number in this course assumes cosine.
        metadata={"hnsw:space": "cosine"},
    )

    batch = 256
    for start in range(0, len(chunks), batch):
        window = chunks[start : start + batch]
        collection.add(
            ids=[f"{c.source}#{c.index}" for c in window],
            documents=[c.text for c in window],
            embeddings=embed([c.text for c in window]),
            metadatas=[
                {"source": c.source, "index": c.index, "produced_by": c.produced_by}
                for c in window
            ],
        )

    return len(chunks)


def search(
    question: str,
    top_k: int | None = None,
    corpus: str | None = None,
    variant: str = "default",
) -> list[Result]:
    """
    Retrieve the chunks closest in meaning to a question.

    Returns them nearest-first, each with its distance.
    """
    top_k = top_k or config.TOP_K
    name = config.collection_name(corpus, variant)

    try:
        collection = _client().get_collection(name)
    except Exception as exc:
        raise RuntimeError(
            f"No index called '{name}'. Run `python app.py index` first."
        ) from exc

    # With hybrid search on, pull a wider pool of candidates so BM25 has
    # something to re-rank. With it off, this is the plain top-k it always was.
    pool = config.BM25_POOL if config.HYBRID else top_k
    raw = collection.query(
        query_embeddings=embed([question]),
        n_results=min(max(pool, top_k), collection.count()),
    )

    candidates: list[Result] = []
    for text, meta, distance in zip(
        raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
    ):
        candidates.append(
            Result(
                text=text,
                source=str(meta.get("source", "unknown")),
                label=f"{meta.get('source', 'unknown')}#{meta.get('index', 0)}",
                distance=float(distance),
                produced_by=str(meta.get("produced_by", "unknown")),
            )
        )

    if not config.HYBRID:
        return candidates[:top_k]

    return _rerank(question, candidates)[:top_k]


def _tokenise(text: str) -> list[str]:
    """Lowercase word tokens. BM25 matches literal words, so punctuation goes."""
    import re

    return re.findall(r"[a-z0-9$.]+", text.lower())


def _rerank(question: str, candidates: list[Result]) -> list[Result]:
    """
    Re-rank semantic candidates by blending their similarity with a BM25 score.

    Both signals are min-max normalised across the candidate pool first, because
    a cosine distance and a BM25 score are not on the same scale. The blend is
    HYBRID_ALPHA * semantic + (1 - HYBRID_ALPHA) * keyword.

    I started with reciprocal rank fusion and it changed nothing. The reason is
    worth recording: for the Old Brewhouse question, the wrong building's
    laundry post out-ranked the right building's overview on BOTH lists, and RRF
    only ever sees ranks. BM25 scored them 6.9 against 7.6 — a real gap that
    rank fusion throws away. Blending the scores keeps it.

    Distances are left exactly as Chroma returned them. The relevance gate
    compares a real cosine distance against the cutoff measured in Milestone 4,
    and re-ranking must not quietly change what that number means.
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:
        raise RuntimeError(
            "Hybrid search needs rank-bm25. Run `pip install -r requirements.txt`, "
            "or set HYBRID = False in config.py."
        ) from exc

    if len(candidates) < 2:
        return candidates

    bm25 = BM25Okapi([_tokenise(c.text) for c in candidates])
    keyword = list(bm25.get_scores(_tokenise(question)))
    semantic = [1.0 - c.distance for c in candidates]

    def normalise(values: list[float]) -> list[float]:
        low, high = min(values), max(values)
        if high - low < 1e-9:
            return [0.0 for _ in values]
        return [(v - low) / (high - low) for v in values]

    sem = normalise(semantic)
    key = normalise(keyword)
    alpha = config.HYBRID_ALPHA

    blended = sorted(
        range(len(candidates)),
        key=lambda i: -(alpha * sem[i] + (1 - alpha) * key[i]),
    )
    return [candidates[i] for i in blended]


def index_exists(corpus: str | None = None, variant: str = "default") -> bool:
    """Is there an index here to search, without searching it?

    `serve.py`'s health check asks this. It deliberately does not embed
    anything: loading the embedding model takes 80 MB and a few seconds, and a
    health check that heavy is a health check nobody can afford to call.
    """
    try:
        collection = _client().get_collection(config.collection_name(corpus, variant))
        return collection.count() > 0
    except Exception:
        return False


def reset():
    """Delete every index. Occasionally the fastest way out of a mess."""
    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)
