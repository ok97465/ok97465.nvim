r"""Test.

Todo:
    None

:auther: ok97465
:Date created: 21.09.17 23:05:16
"""
# %% Import
# Standard library imports
import ast
import json
import os.path as osp
from collections import defaultdict
from textwrap import dedent

# Third party imports
import pynvim
from pyflakes import checker
from pyflakes.messages import UndefinedName


@pynvim.plugin
class Ok97465Plugin(object):
    """내가 사용할 간단한 Plugin."""

    def __init__(self, nvim):
        """Init."""
        self.nvim = nvim
        self.dir_plugin: str = osp.dirname(osp.realpath(__file__))
        self.dir_working: str = ""
        self.import_list_plugin = self.read_import_json(
            osp.join(self.dir_plugin, "autoimport_for_python.json")
        )
        self.import_list_working = defaultdict(list)

    def read_import_json(self, path_json: str) -> dict:
        """Json file에서 import list를 읽어온다."""
        ret = defaultdict(list)
        if not osp.isfile(path_json):
            return ret

        data = open(path_json).read()
        import_info = json.loads(data)

        if "alias" in import_info:
            for alias, module in import_info["alias"].items():
                if alias != module:
                    import_text = "import {} as {}".format(module, alias)
                else:
                    import_text = "import {}".format(module)
                ret[alias].extend([import_text])

        if "module" in import_info:
            for module, func_list in import_info["module"].items():
                if isinstance(func_list, str):
                    func_list = [func_list]
                if isinstance(func_list, list):
                    for func in func_list:
                        import_text = "from {} import {}".format(module, func)
                        ret[func].extend([import_text])

        return ret

    def get_undefine_list(self):
        """Get undefine list."""
        input = "\n".join(self.nvim.current.buffer)

        tree = ast.parse(dedent(input))
        file_tokens = checker.make_tokens(dedent(input))

        w = checker.Checker(tree, file_tokens=file_tokens)
        undefine_list = [
            o.message_args[0] for o in w.messages if isinstance(o, UndefinedName)
        ]

        return undefine_list

    def no_line_of_docstring(self):
        """Docstring Line number를 읽어온다."""
        buf = self.nvim.current.buffer
        no_line_max = min(len(buf), 30)

        found_start = False
        for no_line in range(no_line_max):
            line = buf[no_line]
            if found_start is False:
                if line.startswith(("'''", '"""', "r'''", 'r"""')):
                    found_start = True
            if found_start:
                if line.endswith(("'''", '"""')):
                    return no_line

        return 0

    def no_line_of_import(self):
        """Import가 수행되는 Line number를 읽어온다."""
        buf = self.nvim.current.buffer
        no_line_max = min(len(buf), 80)

        no_line_comment_for_import = 0
        for no_line in range(no_line_max):
            line = buf[no_line]
            if line.startswith(
                (
                    "# %% Import",
                    "# Standard library imports",
                    "# Local imports",
                    "# Third party imports",
                )
            ):
                no_line_comment_for_import = no_line
            if line.startswith(("from ", "import ")):
                return no_line

        return no_line_comment_for_import

    def get_import_list(self) -> dict:
        """Get import list.

        Vim working directory에 import json 파일이 있는 경우 json 파일을 읽어와서 list를
        반환하고 없는 경우 default list를 반환한다.
        """
        cwd = self.nvim.eval("getcwd()")
        if self.dir_working != cwd:
            self.dir_working = cwd
            self.import_list_working = defaultdict(list)

            list1 = self.read_import_json(osp.join(cwd, "autoimport_for_python.json"))
            list2 = self.read_import_json(osp.join(cwd, "autoimport_for_project.json"))

            self.import_list_working.update(list1)
            self.import_list_working.update(list2)

        if len(self.import_list_working) > 0:
            return self.import_list_working
        else:
            return self.import_list_plugin

    @pynvim.command("ImportFromJson")
    def import_from_json(self):
        """Json에서 module list을 읽어와서 Auto import 한다."""
        undefine_list = self.get_undefine_list()

        if not undefine_list:
            self.nvim.command("Isort")
            return

        buf = self.nvim.current.buffer
        no_line_docstring = self.no_line_of_docstring()
        no_line_import = self.no_line_of_import()
        no_line = max(no_line_docstring, no_line_import)
        no_line = min(no_line, len(buf))

        import_list = self.get_import_list()
        for undefine in undefine_list:
            if undefine not in import_list:
                continue
            # Todo: select candidates
            txt_import = import_list[undefine][0]
            buf[no_line + 1 : no_line + 1] = [txt_import]

        self.nvim.command("Isort")
