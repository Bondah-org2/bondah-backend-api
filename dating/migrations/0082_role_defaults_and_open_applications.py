"""
Phase 11 data:

1. Admin roles get default flags that match their names (the admin app has
   been showing these defaults, but the rows only had the model defaults).
   A role whose flags were already changed by hand is left alone.
2. ID documents waiting for review under the old flow (no application row)
   become pending applications, so they show up in the new review queue.
"""

from django.db import migrations

FLAGS = (
    "can_view_overview",
    "can_view_applications",
    "can_view_withdrawals",
    "can_view_reports",
    "can_approve_applications",
    "can_manage_team",
)
MODEL_DEFAULTS = {f: f == "can_view_overview" for f in FLAGS}

ROLE_DEFAULTS = {
    "super_admin": set(FLAGS),
    "admin": set(FLAGS),
    "manager": {"can_view_overview", "can_view_applications", "can_approve_applications", "can_view_withdrawals", "can_view_reports"},
    "moderator": {"can_view_overview", "can_view_applications", "can_approve_applications", "can_view_reports"},
    "finance": {"can_view_overview", "can_view_withdrawals", "can_view_reports"},
    "support": {"can_view_overview", "can_view_applications"},
    "viewer": {"can_view_overview"},
}


def seed_roles(apps, schema_editor):
    AdminRole = apps.get_model("dating", "AdminRole")
    for name, on in ROLE_DEFAULTS.items():
        role = AdminRole.objects.filter(name=name).first()
        wanted = {f: f in on for f in FLAGS}
        if role is None:
            AdminRole.objects.create(name=name, **wanted)
        elif {f: getattr(role, f) for f in FLAGS} == MODEL_DEFAULTS:
            for f, v in wanted.items():
                setattr(role, f, v)
            role.save()


def open_applications(apps, schema_editor):
    DocumentVerification = apps.get_model("dating", "DocumentVerification")
    SelfieVerification = apps.get_model("dating", "SelfieVerification")
    BondmakerApplication = apps.get_model("dating", "BondmakerApplication")

    pending = (
        DocumentVerification.objects.filter(status="pending", user__is_matchmaker=False)
        .order_by("user_id", "-uploaded_at")
    )
    seen = set()
    for doc in pending.iterator():
        if doc.user_id in seen or BondmakerApplication.objects.filter(user_id=doc.user_id, status="pending").exists():
            continue
        seen.add(doc.user_id)
        selfie = (
            SelfieVerification.objects.filter(document_verification=doc, status="pending")
            .order_by("-created_at")
            .first()
        )
        BondmakerApplication.objects.create(
            user_id=doc.user_id,
            document=doc,
            selfie=selfie,
            status="pending",
            submitted_at=doc.uploaded_at,
            snapshot={"migrated": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("dating", "0081_onboarding_and_roles"),
    ]

    operations = [
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
        migrations.RunPython(open_applications, migrations.RunPython.noop),
    ]
