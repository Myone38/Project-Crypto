from datetime import datetime, timedelta


from app.database import Database


def test_save_and_get_equity(tmp_path):
    db_dir = tmp_path / "data"
    db_path = db_dir / "test.db"

    db = Database(str(db_path))
    assert db.save_equity(123.45) is True

    all_eq = db.get_equity_all()
    assert len(all_eq) == 1
    ts, val = all_eq[0]
    assert abs(val - 123.45) < 1e-6


def test_save_and_get_candles(tmp_path):
    db_dir = tmp_path / "data"
    db_path = db_dir / "test.db"

    db = Database(str(db_path))

    now = datetime.now()
    candles = [
        [int(now.timestamp() * 1000), 1, 2, 0.5, 1.5, 10],
        [int((now + timedelta(minutes=1)).timestamp() * 1000), 1.5, 2.5, 1.2, 2.0, 8]
    ]

    inserted = db.save_candles('BTC-EUR', '1m', candles)
    assert inserted == 2

    res = db.get_candles('BTC-EUR', '1m', limit=10)
    assert len(res) == 2

    # Ensure timestamps are stored as UTC ISO strings ending with 'Z'
    for c in res:
        assert isinstance(c['timestamp'], str)
        assert c['timestamp'].endswith('Z')
