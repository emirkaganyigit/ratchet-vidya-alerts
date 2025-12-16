import numpy as np
import pandas as pd

from src.indicators.vidya import vidya


def test_vidya_index_alignment():
    s = pd.Series([1, 2, 3, 4, 5], index=pd.RangeIndex(5))
    v = vidya(s, vma_length=5, momentum_length=2)
    assert (v.index == s.index).all()


def test_vidya_constant_series_stable_after_start():
    s = pd.Series([10.0] * 60)
    v = vidya(s, vma_length=10, momentum_length=5)

    valid = v.dropna()
    assert len(valid) > 0
    assert np.allclose(valid.values, 10.0, atol=1e-9)


def test_vidya_rejects_invalid_lengths():
    s = pd.Series([1.0, 2.0, 3.0])
    try:
        vidya(s, vma_length=0, momentum_length=2)
        assert False
    except ValueError:
        assert True
