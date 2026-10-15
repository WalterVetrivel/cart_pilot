"""Write the seed catalogue to Firestore (idempotent: fixed document ids).

python -m seed.load                         # real Firestore (GOOGLE_CLOUD_PROJECT)
FIRESTORE_EMULATOR_HOST=localhost:8081 python -m seed.load   # local emulator
"""

import os

from google.cloud import firestore

from seed.generate_seed import generate


def main() -> None:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or "cartpilot-511717"
    db = firestore.Client(project=project)
    stores, products = generate()

    batch, pending = db.batch(), 0
    for doc_id, collection, data in [
        *((s["store_id"], "stores", s) for s in stores),
        *((p["product_id"], "products", p) for p in products),
    ]:
        batch.set(db.collection(collection).document(doc_id), data)
        pending += 1
        if pending == 400:  # Firestore batches cap at 500 writes
            batch.commit()
            batch, pending = db.batch(), 0
    if pending:
        batch.commit()

    target = os.environ.get("FIRESTORE_EMULATOR_HOST", f"project {project}")
    print(f"Loaded {len(stores)} stores and {len(products)} products into {target}")


if __name__ == "__main__":
    main()
