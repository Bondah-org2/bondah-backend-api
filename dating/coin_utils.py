from .models import PuzzleVerification


def has_solved_puzzle(user, min_required=1):
    return (
        PuzzleVerification.objects.filter(user=user, is_correct=True).count()
        >= min_required
    )
