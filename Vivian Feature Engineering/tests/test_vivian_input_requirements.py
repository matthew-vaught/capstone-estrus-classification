from estrus.contracts import input_requirements


def test_vivian_recording_requirements_are_preserved_without_other_contributors():
    notes = input_requirements(["vivian__adj_ultradian_amp"])
    assert len(notes) == 1
    assert "complete recording" in notes[0]
    assert "no labels or other mice" in notes[0]
    assert "uncentered" in notes[0]

