from django.contrib.auth.decorators import user_passes_test


def get_current_specialist(user):
    if not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'specialist', None)


def is_head_officer_user(user):
    specialist = get_current_specialist(user)
    if getattr(user, 'is_superuser', False):
        return True
    return bool(specialist and specialist.type == specialist.Type.HEAD_OFFICER)


def is_regional_specialist_user(user):
    specialist = get_current_specialist(user)
    return bool(specialist and specialist.type == specialist.Type.REGIONAL_SPECIALIST)


head_officer_required = user_passes_test(is_head_officer_user)