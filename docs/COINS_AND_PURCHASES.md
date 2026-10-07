# Coins and store purchases

How BondCoins move, how they are bought, and how to set up RevenueCat.

## The ledger

Every balance change goes through `dating/services/wallet_service.py`. Nothing else may update `Wallet` balances.

- Each change locks the wallet row and writes a `WalletTransaction` with a unique `idempotency_key`. Repeating an operation with the same key returns the first result and moves nothing, so retries, double taps and redelivered webhooks are safe.
- The database refuses negative `available_balance` and `locked_balance`.
- `payment_method` on a ledger row is its kind (`purchase`, `match_request`, `gift_sent` and so on). The API also exposes it as `kind`.

| Operation | Effect |
|---|---|
| `credit` / `debit` | Add to or take from the available balance. |
| `hold` | Move coins from available to locked. The row stays `pending`. |
| `capture` | Spend a hold (row becomes `completed`), optionally paying a recipient the full amount. |
| `release` | Return a hold to available (row becomes `cancelled`). |
| `credit_purchase` | Credit bought coins; outstanding coin debt is paid first. |
| `claw_back` | A store refund: take back what is left, record the rest as `coin_debt`, flag the wallet after 2 refunds in 90 days. |

### Escrow rules

| Action | Hold | Accepted | Rejected or no answer in 7 days |
|---|---|---|---|
| Like (match request) | 1 coin, server-set | Paid to the bondmaker | Refunded |
| Private visibility | 10 coins | Paid to the bondmaker, visible 30 days | Refunded |
| Public visibility | Free | Visible 30 days | Nothing to refund |

`dating.tasks.expire_stale_coin_holds` runs hourly (Celery beat) and refunds anything undecided after 7 days.

Bondmaker earnings (`total_earnings`) only count `match_request_earning`, `private_visibility_earning` and `gift_converted`.

## Buying coins

The app buys through RevenueCat. The backend credits coins only when RevenueCat's webhook says the purchase went through:

1. The app signs RevenueCat in with the backend user ID as the app user ID.
2. The user buys `bondah_coins_<amount>` in the store sheet.
3. RevenueCat calls `POST /api/v1/webhooks/revenuecat/`. The event is stored in `RevenueCatEvent` (unique by event ID) and applied in Celery.
4. The coin amount comes from our `BondcoinPackage` catalog, never from the payload. The ledger key `purchase:<store>:<store transaction id>` makes each store transaction count once.
5. The app polls the ledger until the purchase appears, then shows the new balance.

A failed event (unknown product, unknown user) is kept with its error. Fix the cause, then press **Retry** in the admin app under **Finance > Store events**.

## RevenueCat setup checklist

**Products** (same IDs in App Store Connect, Google Play and RevenueCat; consumables / in-app products):

| Product ID | Coins | Reference price |
|---|---|---|
| `bondah_coins_10` | 10 | $0.89 |
| `bondah_coins_30` | 30 | $2.67 |
| `bondah_coins_50` | 50 | $4.45 |
| `bondah_coins_100` | 100 | $8.90 |
| `bondah_coins_300` | 300 | $26.70 |
| `bondah_coins_500` | 500 | $44.50 |
| `bondah_coins_800` | 800 | $71.20 |
| `bondah_coins_1200` | 1200 | $106.80 |
| `bondah_coins_2000` | 2000 | $178.00 |

Store prices snap to each store's price tiers; the app always shows the store's localized price. Migration `0068_seed_coin_packages` creates this catalog.

**Apps in RevenueCat**: Play Store app `com.bondah.matchmaking` (service account JSON uploaded, Google developer notifications on) and App Store app `com.bondah.matchmaking` (In-App Purchase key uploaded).

**Webhook** (RevenueCat > Integrations > Webhooks):

- URL: `https://<api host>/api/v1/webhooks/revenuecat/`
- Authorization header: the value of `REVENUECAT_WEBHOOK_AUTH`. Generate one with `python -c "import secrets;print(secrets.token_urlsafe(48))"`.

**Server environment**:

| Variable | Value |
|---|---|
| `REVENUECAT_WEBHOOK_AUTH` | The shared webhook secret. If empty, the webhook answers 503. |
| `REVENUECAT_SECRET_KEY` | Secret API key (`sk_...`). Server only. Used from rebuild phase 2. |
| `REVENUECAT_PROJECT_ID` | RevenueCat project ID. |
| `REVENUECAT_ALLOW_SANDBOX` | `true` only on dev/staging. In production, sandbox purchases are stored and ignored. |

**App** (`app.json` > `expo.extra.revenuecat`): `androidApiKey` (`goog_...`) and `iosApiKey` (`appl_...`). These are public keys. Changing native modules means a new development build; the RevenueCat SDK does not work in Expo Go.

## Subscriptions (Pro and Prime)

| Product ID | Plan | Period | Reference price |
|---|---|---|---|
| `bondah_pro_monthly` | Pro | 1 month | $9.99 |
| `bondah_pro_3month` | Pro | 3 months | $24.99 |
| `bondah_prime_monthly` | Prime | 1 month | $19.99 |
| `bondah_prime_3month` | Prime | 3 months | $49.99 |

Create them as auto-renewing subscriptions in both stores (same IDs; on Google Play use one subscription per ID with a single base plan) and add them to the RevenueCat offering. Migration `0071_seed_subscription_plans` creates the plans and ends any subscription without a store transaction (those were created through the old open API without paying).

| | Free | Pro | Prime |
|---|---|---|---|
| Swipes (likes and passes) | 10 a day | Unlimited | Unlimited |
| Undo | No | Yes | Yes |
| Read receipts | No | No | Yes |
| Swipe deck | Own country | Own country | Any country (`?scope=global` or `?country=`) |

Bondmakers always see read receipts.

How it works:

- `dating/services/subscription_service.py` computes a user's entitlements from their active `UserSubscription` rows (cached for up to 60 seconds, never past the expiry) and is the only place features are decided.
- RevenueCat lifecycle events (purchase, renewal, cancellation, refund, expiration, billing issue with grace, transfer) update one `UserSubscription` per store subscription (`store` + `original_transaction_id`). Events older than the last one applied are ignored.
- The daily limit is counted in `DailySwipeCount` per user and local day. The app sends `X-Timezone`; the limit resets at the user's midnight. Over the limit, `users/interact/` answers 429 with `code: "swipe_limit"` and `resets_at`.
- Endpoints: `GET subscriptions/plans/`, `GET subscriptions/current/` (entitlements), `GET swipes/quota/`, `POST users/interact/undo/` (Pro and Prime).

## Admin

The admin app (Bondah-Admin-System) has:

- **Finance > Subscriptions** (`withdrawals` permission): active, billing-issue and ended subscriptions by plan.
- **Overview**: active Pro and Prime counts, billing issues and net store revenue.
- **Finance > Flagged wallets** (`withdrawals` permission): repeated refunders and coin debt, with "Reviewed" to clear the flag.
- **Finance > Store events** (`withdrawals` permission): every RevenueCat event, its payload, and Retry for failed ones.
- **Settings** (principal admin only): the gift conversion rate.
