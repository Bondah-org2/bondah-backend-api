"""Give pre-ledger pending requests a proper hold row.

Before the ledger, a like or private visibility request moved coins into the
wallet's locked balance without any record the code could settle later. This
links each still-pending request to a "pending" hold row so accept, reject
and expiry can capture or refund it.

Balances are not changed (the coins are already locked). Per wallet, holds
are adopted oldest first only while they fit inside the locked balance, so a
release can never push it below zero. Anything that doesn't fit is reported
and left without a hold; rejecting or expiring it then refunds nothing.
"""

from collections import defaultdict

from django.db import migrations

LIKE_KIND = "match_request"
VISIBILITY_KIND = "private_visibility"
PRIVATE_COST = 10


def adopt(apps, schema_editor):
    Wallet = apps.get_model("dating", "Wallet")
    WalletTransaction = apps.get_model("dating", "WalletTransaction")
    MatchRequest = apps.get_model("dating", "MatchRequest")
    Visibility = apps.get_model("dating", "Visibility")

    # (created_at, kind, object, user_id, amount) for every pending request with coins locked.
    candidates = []
    for mr in MatchRequest.objects.filter(status="pending", hold_transaction__isnull=True):
        if mr.coins_charged and mr.coins_charged > 0:
            candidates.append((mr.created_at, LIKE_KIND, mr, mr.requester_id, mr.coins_charged))
    for vis in Visibility.objects.filter(
        status="pending", visibility="private", hold_transaction__isnull=True
    ):
        candidates.append((vis.updated_at, VISIBILITY_KIND, vis, vis.owner_id, PRIVATE_COST))
    candidates.sort(key=lambda c: c[0])

    remaining = {
        w.user_id: w.locked_balance
        for w in Wallet.objects.filter(user_id__in={c[3] for c in candidates})
    }
    # Holds that already exist for these users count against the locked balance.
    for row in WalletTransaction.objects.filter(
        user_id__in=remaining.keys(), status="pending", idempotency_key__isnull=False
    ):
        remaining[row.user_id] -= row.amount

    skipped = defaultdict(int)
    for _, kind, obj, user_id, amount in candidates:
        if remaining.get(user_id, 0) < amount:
            skipped[kind] += 1
            continue

        if kind == LIKE_KIND:
            key = f"hold:match_request:{obj.id}"
            hold = WalletTransaction.objects.create(
                user_id=user_id, tx_type="debit", amount=amount, payment_method=kind,
                reference_id=f"match_request:{obj.id}", idempotency_key=key, status="pending",
            )
        else:
            # The old code wrote an unkeyed pending row; reuse it when it is there.
            hold = (
                WalletTransaction.objects.filter(
                    user_id=user_id, payment_method=kind, status="pending",
                    reference_id=str(obj.id), idempotency_key__isnull=True,
                ).first()
            )
            if hold is None:
                hold = WalletTransaction.objects.create(
                    user_id=user_id, tx_type="debit", amount=amount, payment_method=kind,
                    reference_id=f"visibility:{obj.id}", status="pending",
                )
            hold.idempotency_key = f"hold:visibility:{obj.id}:legacy"
            hold.save(update_fields=["idempotency_key"])

        obj.hold_transaction_id = hold.id
        obj.save(update_fields=["hold_transaction"])
        remaining[user_id] -= amount

    if skipped:
        print(f"\n  Pending requests left without a hold (locked balance too low): {dict(skipped)}")


class Migration(migrations.Migration):

    dependencies = [
        ("dating", "0068_seed_coin_packages"),
    ]

    operations = [
        migrations.RunPython(adopt, migrations.RunPython.noop),
    ]
