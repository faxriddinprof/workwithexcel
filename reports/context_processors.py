from .decorators import get_current_specialist, is_head_officer_user, is_regional_specialist_user


def specialist_context(request):
    specialist = get_current_specialist(request.user)
    return {
        'current_specialist': specialist,
        'is_head_officer': is_head_officer_user(request.user),
        'is_regional_specialist': is_regional_specialist_user(request.user),
    }