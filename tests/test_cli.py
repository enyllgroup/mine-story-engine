import pytest
from minestory.__main__ import main

@pytest.mark.parametrize("command",["produce","prepare","finish","version","analyze","plan","render","qc","assets","doctor","validate","launcher","cache"])
def test_each_cli_parser_can_show_help(command):
    with pytest.raises(SystemExit) as info:
        main([command,"--help"])
    assert info.value.code==0
