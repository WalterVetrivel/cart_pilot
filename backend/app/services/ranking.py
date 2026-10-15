"""Per-item candidate scoring (SPEC §8.2)."""

from app.models.schemas import Candidate, ScoredCandidate, Weights

FEW_REVIEWS = 20


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def rank_candidates(candidates: list[Candidate], stores: dict[str, dict], weights: Weights) -> list[ScoredCandidate]:
    """Scores every candidate for one item, best first. Out-of-stock ones stay listed but score lowest.

    Price is compared on line_price (the cost of covering the requested quantity), not per-unit price,
    so a 10 kg pack never beats a 1 kg pack for a 1 kg request just by being cheaper per kg.
    """
    if not candidates:
        return []
    w = weights.normalised()
    in_stock = [c for c in candidates if c.in_stock] or candidates
    min_price = min(c.line_price for c in in_stock)
    max_eta = max(stores[c.store_id]["eta_minutes"] for c in candidates) or 1

    scored = []
    for c in candidates:
        store = stores[c.store_id]
        price_score = min_price / c.line_price if c.line_price > 0 else 1.0
        rating_score = _clamp((c.rating - 3.0) / 2.0) * (0.7 if c.rating_count < FEW_REVIEWS else 1.0)
        delivery_score = 1 - store["eta_minutes"] / max_eta
        avail_score = 1.0 if c.in_stock else 0.0
        score = (
            w.price * price_score + w.rating * rating_score + w.delivery * delivery_score + w.availability * avail_score
        )
        if c.brand_match:  # SPEC §8.1: boost the brand the user asked for
            score += 0.05
        scored.append(
            ScoredCandidate(
                **c.model_dump(),
                score=round(score, 4),
                price_score=round(price_score, 4),
                rating_score=round(rating_score, 4),
                delivery_score=round(delivery_score, 4),
                eta_minutes=store["eta_minutes"],
                eta_label=store["eta_label"],
            )
        )
    scored.sort(key=lambda s: (not s.in_stock, -s.score, s.line_price))
    return scored
