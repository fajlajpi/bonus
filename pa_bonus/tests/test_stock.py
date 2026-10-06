import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from pa_bonus.models import User, FileUpload, Reward
from pa_bonus.tasks import process_stock_file


def make_reward(code, availability='ON_DEMAND', stock=None):
    return Reward.objects.create(
        abra_code=code,
        name=code,
        point_cost=10,
        description='',
        availability=availability,
        stock=stock,
    )


@pytest.mark.django_db
class TestProcessStockFile:
    @pytest.fixture(autouse=True)
    def media_root(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path

    def run_upload(self, rows):
        content = "katalog;Počet\n" + "".join(f"{code};{qty}\n" for code, qty in rows)
        user = User.objects.create(username="manager", user_number="M1", user_phone="1")
        upload = FileUpload.objects.create(
            file=SimpleUploadedFile("stock.csv", content.encode("utf-8")),
            uploaded_by=user,
        )
        process_stock_file(upload.id)
        upload.refresh_from_db()
        return upload

    def test_sets_availability_and_stock_from_quantity(self):
        for code in ("R1", "R2", "R3", "R4"):
            make_reward(code)

        upload = self.run_upload([("R1", 10), ("R2", 3), ("R3", 0), ("R4", "")])

        assert upload.status == 'COMPLETED'
        expected = {
            "R1": ('AVAILABLE', 10),
            "R2": ('AVAILABLE_LAST_UNITS', 3),
            "R3": ('ON_DEMAND', 0),
            "R4": ('ON_DEMAND', None),
        }
        for code, (availability, stock) in expected.items():
            reward = Reward.objects.get(abra_code=code)
            assert (reward.availability, reward.stock) == (availability, stock)

    def test_manual_statuses_are_kept_but_stock_is_updated(self):
        make_reward("U1", availability='UNAVAILABLE')
        make_reward("T1", availability='TEMP_UNAVAILABLE')
        make_reward("T2", availability='TEMP_UNAVAILABLE')

        self.run_upload([("U1", 50), ("T1", 0), ("T2", 3)])

        assert Reward.objects.get(abra_code="U1").availability == 'UNAVAILABLE'
        assert Reward.objects.get(abra_code="U1").stock == 50
        assert Reward.objects.get(abra_code="T1").availability == 'TEMP_UNAVAILABLE'
        assert Reward.objects.get(abra_code="T1").stock == 0
        assert Reward.objects.get(abra_code="T2").availability == 'TEMP_UNAVAILABLE'
        assert Reward.objects.get(abra_code="T2").stock == 3

    def test_reward_missing_from_file_is_untouched(self):
        make_reward("R1")
        make_reward("OLD", availability='AVAILABLE', stock=7)

        self.run_upload([("R1", 10)])

        reward = Reward.objects.get(abra_code="OLD")
        assert (reward.availability, reward.stock) == ('AVAILABLE', 7)
