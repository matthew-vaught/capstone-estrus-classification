from estrus.contracts import input_requirements


def test_alisha_recording_requirements_are_preserved_without_other_contributors():
    notes = input_requirements(["alisha__dtw_shift_whole_temp"])
    assert len(notes) == 1
    assert "other 13 recording days" in notes[0]
    assert "complete 14-day recording" in notes[0]
    assert "no labels or other mice" in notes[0]
    assert input_requirements(["baseline__cbt_mean"]) == []

