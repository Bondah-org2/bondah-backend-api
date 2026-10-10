# Onboarding, roles and account status

Rebuild phase 11. The code is in `dating/services/onboarding_service.py`, `dating/authentication.py`, `dating/permissions.py` and `dating/views/onboarding.py`.

## App roles

| Concept | Where | Meaning |
| --- | --- | --- |
| Chosen mode | `UserRoleSelection.selected_role` | What the person last picked: `looking_for_love` or `bondmaker`. Grants nothing on its own. |
| Approved bondmaker | `User.is_matchmaker` | Set only when Team Bondah approves an application. |
| Active mode | `onboarding_service.active_mode()` | `bondmaker` only for approved bondmakers; otherwise `love_seeker` once the seeker profile is complete. |

Bondmaker-only endpoints use `IsApprovedBondmaker`. Its 403 body is `{"detail": ..., "code": "bondmakers_only"}`.

## Onboarding state

`GET onboarding/state/` returns where the app should go next. The same object also comes back as `onboarding` from login, role selection and application submit.

```json
{
  "next": "choose_role | seeker_setup | bondmaker_setup | application_status | app",
  "selected_role": "looking_for_love | bondmaker | null",
  "active_mode": "love_seeker | bondmaker | null",
  "is_bondmaker": false,
  "account": {"status": "active | restricted | banned", "reason": ""},
  "seeker_profile": {"complete": false, "missing": ["profile_picture"]},
  "bondmaker_application": null,
  "application_missing": ["id_document"]
}
```

A complete seeker profile has: name, gender, date of birth, profile picture and preferred gender.

A pending or rejected applicant who has a complete seeker profile uses the app as a love seeker. One without a complete seeker profile sees `application_status`.

## Bondmaker applications

1. The setup steps save the profile through `PATCH bondmaker/profile/update/`. This covers answers (`security_questions_update`), `skills`, `business_type`, `provides_guidance` and `social_handles`. The ID document goes to `document-verification/` and the selfie to `upload/selfie/`.
2. `GET bondmaker/application/` lists what's still missing. `POST` submits, which ties the pending document, its selfie and a snapshot of the profile into one `BondmakerApplication`.
3. Team Bondah reviews it with `POST admin/applications/<id>/review/` and `{action, note, redo_identity}`:
   - `approve`: the person becomes a bondmaker and their mode switches to bondmaker.
   - `reject`: needs a note. They can apply again after 30 days (`reapply_after`).
   - `request_changes`: needs a note. The same application reopens. With `redo_identity` the ID and selfie are rejected, so new ones must be uploaded.

A person can have only one open application (pending or changes requested); a database constraint enforces this. A submitted ID document is read-only.

Required to submit: name, gender, date of birth, username, thought leadership, a profile picture, at least one skill, the five answers (data protection, scam prevention, user verification, business or community, relationship guidance), at least one social link, a pending ID document and a selfie for it.

## Account status

| Status | Effect |
| --- | --- |
| `active` | Normal. |
| `restricted` | Read-only. Every write returns 403 `{"code": "account_restricted", "detail": <reason>}`, except those listed in `RESTRICTED_ALLOWED_VIEWS` (sign out, refresh, devices, settings, delete account, 2FA, choosing a mode). |
| `banned` | Sign-in, refresh and every request return 401 `{"code": "account_banned"}`. All sessions are signed out. |

The check runs in `StatusAwareJWTAuthentication`, so tokens issued before the change stop working at once. Team Bondah sets the status with `POST admin/users/<id>/status/` and `{status, reason}`; a reason is required unless the status is `active`. Each change is recorded in `AccountStatusChange`.

## Admin team roles

- The per-person `AdminPermission` flags are the only source of truth. An `AdminRole` only fills in default flags when someone is created or changes role. Migration 0082 gives each role sensible defaults.
- The principal admin has every flag. A member who is `inactive` or no longer staff has none.
- Admin login and `GET admin/me/` return `permissions` (sections: overview, applications, withdrawals, reports, team) and `flags`. The admin app reads these instead of guessing from the role name.
- Anyone with `can_manage_team` can manage the team. They can't grant a flag they don't hold, can't edit the principal admin, and can't change their own access.
- Removing a member takes away their admin access and signs them out. The user row is kept.

## Sign-in hardening

- OTP codes are generated with `secrets` and never logged.
- A code stops working after 5 wrong tries (`EmailVerification.failed_attempts`). Resending resets the count.
- The age check runs once. Profile edits can't change the email (that goes through Settings) or the date of birth.
- Refresh rotates the refresh token, blacklists the old one, and refuses deleted, inactive and banned accounts.
