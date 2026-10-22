from aircursor.config import Config, SLIDERS


def test_defaults_valid_and_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    cfg = Config(); cfg.speed = 1.7; cfg.gestures["fist"] = "left"; cfg.save(p)
    loaded = Config.load(p)
    assert loaded.speed == 1.7 and loaded.gestures["fist"] == "left"
    assert loaded.gestures["pinch"] == "left"


def test_corrupt_or_missing_file_falls_back(tmp_path):
    assert Config.load(tmp_path / "nope.json").speed == 1.0
    p = tmp_path / "bad.json"; p.write_text("{not json")
    assert Config.load(p).speed == 1.0


def test_values_are_clamped_and_bad_mappings_ignored(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"speed": 99, "gestures": {"pinch": "explode", "bogus": "left"}}')
    cfg = Config.load(p)
    hi = [s for s in SLIDERS if s[0] == "speed"][0][3]
    assert cfg.speed == hi and cfg.gestures["pinch"] == "left" and "bogus" not in cfg.gestures


def test_reset_keeps_camera_choice():
    cfg = Config(); cfg.speed = 2.0; cfg.phone_url = "https://x"; cfg.camera_source = "url"
    cfg.reset_to_defaults()
    assert cfg.speed == 1.0 and cfg.phone_url == "https://x" and cfg.camera_source == "url"


def test_old_config_with_boosts_on_is_migrated_off(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"accel_strength": 1.0, "long_move_boost": 0.8, "speed": 1.4}')   # a v1 file (no version)
    cfg = Config.load(p)
    assert cfg.accel_strength == 0 and cfg.long_move_boost == 0 and cfg.speed == 1.4
    cfg.accel_strength = 0.6; cfg.save(p)                                           # a deliberate choice survives
    assert Config.load(p).accel_strength == 0.6
