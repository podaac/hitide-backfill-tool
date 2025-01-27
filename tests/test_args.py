import os
from podaac.hitide_backfill_tool.file_util import write_yaml_file
from podaac.hitide_backfill_tool.args import parse_args

def test_parsing_args_with_config(tmp_path):
    config_path = os.path.join(tmp_path, "test_config.yml")
    test_config = {
        "cmr": "ops",
        "image": "off",
        "use_data_url": True,
        "default_message_config" : "/test/path"
    }
    args = ["--config", config_path, "--collection", "abc", "--image=force", "--preview"]

    write_yaml_file(config_path, test_config)

    config = parse_args(args)

    assert config.cmr == "ops"          # specified in config file
    assert config.collection == "abc"   # specified in cli args
    assert config.footprint == None     # specified as not input
    assert config.image == "force"      # specified in config file, overridden in cli args
    assert config.preview == True       # flag specified in cli args
    assert config.use_data_url == True  # flag specified in config file, NOT overridden in cli args         
