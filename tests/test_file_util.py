from podaac.hitide_backfill_tool.file_util import load_json_file


def test_loading_a_json_file():
    a = load_json_file("resources/sample_granules_1.json",
                       relative_to=__file__)
    assert a["hits"] == 998700
