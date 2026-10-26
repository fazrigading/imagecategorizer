from image_categorizer.viewer import fit_size


def test_fit_wider_than_canvas():
    assert fit_size(4000, 1000, 800, 800) == (800, 200)


def test_fit_taller_than_canvas():
    assert fit_size(1000, 4000, 800, 800) == (200, 800)


def test_fit_upscales_small_image():
    assert fit_size(100, 50, 800, 800) == (800, 400)


def test_typical_photo_is_not_upscaled_past_fit():
    assert fit_size(1600, 1200, 1024, 768) == (1024, 768)
