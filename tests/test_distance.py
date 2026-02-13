from Couches.Backend.app import haversine_m


def test_haversine_zero_distance():
    assert haversine_m(48.8566, 2.3522, 48.8566, 2.3522) == 0.0


def test_haversine_positive_distance():
    distance = haversine_m(48.8566, 2.3522, 48.8570, 2.3525)
    assert distance > 0
