import pytest
from django.contrib.auth.models import Group
from django.test import Client, override_settings
from django.urls import reverse
from pa_bonus.models import User

ALL_ON = {'extra_goals': True, 'point_expiration': True, 'sms_export': True}
ALL_OFF = {'extra_goals': False, 'point_expiration': False, 'sms_export': False}


@pytest.fixture
def client_user(db):
    return User.objects.create_user(username='c', password='x', user_number='1', user_phone='1')


@pytest.fixture
def manager(db):
    u = User.objects.create_user(username='m', password='x', user_number='2', user_phone='2')
    g, _ = Group.objects.get_or_create(name='Managers')
    u.groups.add(g)
    return u


def logged(user):
    c = Client()
    c.login(username=user.username, password='x')
    return c


@pytest.mark.django_db
@pytest.mark.parametrize('flags,expected', [(ALL_ON, 200), (ALL_OFF, 404)])
def test_feature_views_reachable_only_when_enabled(client_user, manager, flags, expected):
    with override_settings(FEATURES=flags):
        assert logged(client_user).get(reverse('point_expiration')).status_code == expected
        assert logged(client_user).get(reverse('extra_goals_detail')).status_code == expected
        assert logged(manager).get(reverse('sms_export')).status_code == expected


@pytest.mark.django_db
def test_client_dashboard_hides_disabled_links(client_user):
    with override_settings(FEATURES=ALL_ON):
        body = logged(client_user).get(reverse('dashboard')).content.decode()
        assert reverse('point_expiration') in body
        assert reverse('extra_goals_detail') in body
    with override_settings(FEATURES=ALL_OFF):
        body = logged(client_user).get(reverse('dashboard')).content.decode()
        assert reverse('point_expiration') not in body
        assert reverse('extra_goals_detail') not in body


@pytest.mark.django_db
def test_manager_dashboard_hides_disabled_sections(manager):
    with override_settings(FEATURES=ALL_ON):
        body = logged(manager).get(reverse('manager_dashboard')).content.decode()
        assert reverse('sms_export') in body
    with override_settings(FEATURES=ALL_OFF):
        body = logged(manager).get(reverse('manager_dashboard')).content.decode()
        assert reverse('sms_export') not in body
        assert 'Points expiring this month' not in body


@pytest.mark.django_db
def test_currency_and_identity_come_from_settings(client_user):
    with override_settings(CURRENCY_SYMBOL='zł', BONUS_PROGRAMME_NAME='Program Bonusowy',
                           COMPANY_NAME='PRIMAVERA PL', FEATURES=ALL_ON):
        body = logged(client_user).get(reverse('dashboard')).content.decode()
        assert 'Program Bonusowy' in body
        assert 'PRIMAVERA PL' in body
        assert 'Kč' not in body
