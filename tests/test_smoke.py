import dds3


def test_dds3_exports():
    assert hasattr(dds3, "solve_board_pbn")
    assert hasattr(dds3, "calc_dd_table")
    assert hasattr(dds3, "par")


def test_solve_board_pbn_returns_score():
    pbn = "N:QJ6.K652.J85.T98 873.J97.AT764.Q4 K5.T83.KQ9.A7652 AT942.AQ4.32.KJ3"
    result = dds3.solve_board_pbn(pbn, trump=1)
    assert "score" in result
