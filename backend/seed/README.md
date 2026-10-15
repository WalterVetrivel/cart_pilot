# Seed data (milestone M1)

- `generate_seed.py`: 4 fictional stores, 75 canonical items, ~600 products, random seed 42 (SPEC §7).
- `load.py`: idempotent Firestore loader, run with `python -m seed.load`.
- `demo_vouchers.json`, `demo_emails/`: voucher demo without a real Gmail inbox.
