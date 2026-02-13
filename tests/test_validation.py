from Couches.Couche3.Validation import Validation


def test_validation_ranges_ok():
    v = Validation()
    assert v.check_temp(20.0)
    assert v.check_humidite(50.0)
    assert v.check_pression(1013.0)
    assert v.check_gps(48.8566, 2.3522)


def test_validation_ranges_ko():
    v = Validation()
    assert not v.check_temp(120.0)
    assert not v.check_humidite(150.0)
    assert not v.check_pression(700.0)
    assert not v.check_gps(300.0, 2.0)
