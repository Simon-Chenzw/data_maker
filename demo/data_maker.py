#!/usr/bin/python3

import os
import sys
import stat
import time
import json
import shutil
import platform
import requests
import argparse
import threading
import subprocess


class config_json:
    # Do not remove the comments below
    # json_name below
    json_name = "config.json"
    version = 'v1.2.0'
    # start of default json_data
    json_data = {
        'ignore_version': [],
        'default_zip_name':
        'problem_data',
        'default_input_exec_type':
        'py',
        'default_output_exec_type':
        'cpp',
        'states_name':
        'states',
        'input_file_name':
        'data%d.in',
        'output_file_name':
        'data%d.out',
        'input_exec_name_list': {
            'py': 'make_in.py',
            'cpp': 'make_in.cpp'
        },
        'output_exec_name_list': {
            'py': 'make_out.py',
            'cpp': 'make_out.cpp'
        },
        'compile_cmd': {
            '_comment':
            'file_head is the name you set in exec_name_list without suffix',
            'cpp': 'g++ {file_head}.cpp -o {file_head}.out -std=c++17 -O3 2>&1'
        },
        'exec_cmd': {
            '_comment':
            'file_head is the name you set in exec_name_list without suffix',
            'py': 'python3 {file_head}.py',
            'cpp': './{file_head}.out'
        },
        'zip_cmd':
        'cd temp && zip -q -m -r ../{zip_name}.zip .',
        'github_url':
        'https://api.github.com/repos/Simon-Chenzw/data_maker/releases'
    }

    # end of default json_data

    def __init__(self):
        self.default_json_data_str = json.dumps(self.json_data, indent=4)
        self.load_json()
        self.script_name = sys.argv[0].split('/')[-1]

    def load_json(self):
        try:
            with open(self.json_name, 'r') as json_file:
                self.json_data.update(json.load(json_file))
        except json.decoder.JSONDecodeError:
            print(
                "The json format is wrong, you can use \"-config_dump\" to overwrite config to the default value"
            )
            print("Use default config")
        except FileNotFoundError:
            # print(f"\"{self.json_name}\" not found, use default config")
            if platform.system().lower() == "Windows":
                print(
                    "please use \"-config_dump\" and change \"compile_cmd exec_cmd zip_cmd\" for your platform"
                )
                exit()

    def dump_default_json(self):
        if os.path.isfile(self.json_name):
            if tool.yesorno("Keep old json?"):
                os.rename(self.json_name, "old_" + self.json_name)
                print("Old json has been renamed to \"old_%s\"" %
                      self.json_name)
        with open(self.json_name, 'w') as fp:
            fp.write(self.default_json_data_str)
        print("Default json has been dumped to \"%s\"" % self.json_name)

    def load_default_json(self):
        print("Warning: This is a dangerous operation.",
              "Before loading, please make sure that your json",
              "is in the format used by the current version.")
        print("You can use \"-config_dump\" to dump default json.")
        input(tool.colorful("-----press enter to continue-----", "red"))
        with open(self.script_name, 'r') as fin:
            codes = [line for line in fin]
        os.rename(self.script_name, "old_" + self.script_name)
        print("Old script has been saved as \"old_%s\"" % self.script_name)
        for i in range(len(codes)):
            if codes[i] == "    # start of default json_data\n":
                default_json_start = i
            if codes[i] == "    # end of default json_data\n":
                default_json_end = i
        with open(self.script_name, 'w') as fout:
            fout.writelines(codes[:default_json_start + 1] +
                            ["    json_data = ",
                             str(self.json_data), "\n"] +
                            codes[default_json_end:])
        print("The default json in the script has been updated")
        os.chmod(self.script_name, stat.S_IXUSR)

    def change_json_name(self, new_name):
        print("Change config file's name to", new_name)
        with open(self.script_name, 'r') as fin:
            codes = [line for line in fin]
        for i in range(len(codes)):
            if codes[i] == "    # json_name below\n":
                codes[i + 1] = f"    json_name = \"{new_name}\"\n"
        with open(self.script_name, 'w') as fout:
            fout.writelines(codes)
        print("Successfully changed")


class argument:
    def __init__(self, json_data):
        self.option = self.get_parser(json_data).parse_args()

    @staticmethod
    def get_parser(json_data):
        # guide https://docs.python.org/3/library/argparse.html
        # help
        parser = argparse.ArgumentParser(
            usage=sys.argv[0].split('/')[-1] + " [name] [-option]",
            description="One simple script for making date in OI",
            epilog=
            "you can use the first letter of the optional arguments as abbreviation, if the abbreviation is unambiguous"
        )
        # 跟工作有关的option
        work_option_group = parser.add_argument_group('work option')
        # 压缩包名字
        work_option_group.add_argument("name",
                                       nargs='?',
                                       default=json_data["default_zip_name"],
                                       help="name of the zip")
        # 修改的in文件个数
        work_option_group.add_argument(
            "-edit",
            nargs='?',
            const=0,
            default=-1,
            type=int,
            help=
            "pause after make input, previous NUM (default:%(const)s) will open in vscode",
            metavar="NUM",
            dest="input_edit_num")
        # 输出out文件细节
        work_option_group.add_argument(
            "-detail",
            action='store_true',
            help="print the detail of all output file",
            dest="output_print")
        # 构造in的语言类型
        work_option_group.add_argument(
            "-input",
            default=json_data["default_input_exec_type"],
            choices=['py', 'cpp'],
            help="the language that make input",
            dest="input_exec_type")
        # 构造out的语言类型
        work_option_group.add_argument(
            "-output",
            default=json_data["default_output_exec_type"],
            choices=['py', 'cpp'],
            help="the language that make output",
            dest="output_exec_type")
        # 需要打包至zip中的文件
        work_option_group.add_argument(
            "-zip",
            nargs='+',
            default=[],
            choices=["in", "out", "states"],
            help="FILE={in,out,states} file(s) put into the zip. " +
            "\"in\" means the code of making input" +
            "\"out\" means the code of making output",
            metavar="FILE",
            dest="zip_file")
        # 需要跳过的流程
        work_option_group.add_argument(
            "-skip",
            nargs='+',
            default=[],
            choices=["in", "out", "zip"],
            help="STAGE={in,out,zip} skip the stage.",
            metavar="STAGE",
            dest="skip")
        # 脚本本体相关
        script_option_group = parser.add_argument_group('script option')
        # version
        script_option_group.add_argument("-version",
                                         action='store_true',
                                         help="print version",
                                         dest="print_version")
        # 通过github更新
        script_option_group.add_argument("-upgrade",
                                         action='store_true',
                                         help="upgrade to the latest version",
                                         dest="install_latest")
        # 通过github安装
        script_option_group.add_argument("-get",
                                         nargs=1,
                                         default=["not_upgrade"],
                                         help="get the selected version",
                                         metavar="version",
                                         dest="install_version")
        # 默认json相关
        script_option_group.add_argument("-config_dump",
                                         action='store_true',
                                         help="make default json file",
                                         dest="json_dump_default")
        script_option_group.add_argument(
            "-config_load",
            action='store_true',
            help="load json file and save as default config",
            dest="json_load_default")
        script_option_group.add_argument("-config_name",
                                         nargs=1,
                                         default=["not_change"],
                                         help="change the config name",
                                         metavar="NEW_NAME",
                                         dest="change_json_name")
        return parser


class config(config_json, argument):
    states = list()
    garbage = list()

    def __init__(self):
        config_json.__init__(self)
        argument.__init__(self, self.json_data)
        self.analyze_scipt_option()
        self.get_states()

    def analyze_scipt_option(self):
        if self.option.install_latest:
            tool.download_version(self, "latest")
            exit()
        if self.option.install_version[0] != "not_upgrade":
            tool.download_version(self, self.option.install_version[0])
            exit()
        if self.option.change_json_name[0] != "not_change":
            self.change_json_name(self.option.change_json_name[0])
            exit()
        if self.option.json_dump_default:
            self.dump_default_json()
            exit()
        if self.option.json_load_default:
            self.load_default_json()
            exit()
        if self.option.print_version:
            print("Version :", self.version)
            exit()

    def get_states(self):
        try:
            with open(self.json_data["states_name"], mode='r') as states_file:
                for line in states_file.read().split('\n'):
                    if line != "":
                        self.states.append(line)
        except FileNotFoundError:
            print("\"%s\" not found" % self.json_data["states_name"])
            exit()

    def input_file(self, num):
        return self.json_data["input_file_name"] % num

    def output_file(self, num):
        return self.json_data["output_file_name"] % num

    def input_exec_name(self):
        return self.json_data["input_exec_name_list"][
            self.option.input_exec_type]

    def output_exec_name(self):
        return self.json_data["output_exec_name_list"][
            self.option.output_exec_type]

    def exec(self, file_type, file_name):
        return self.json_data["exec_cmd"][file_type].format(
            file_head=os.path.splitext(file_name)[0])

    def input_exec(self):
        return self.exec(self.option.input_exec_type, self.input_exec_name())

    def output_exec(self):
        return self.exec(self.option.output_exec_type, self.output_exec_name())


class tool:
    @staticmethod
    def yesorno(output_str):
        while True:
            s = input(tool.colorful(output_str + " [Y/n] ", "purple"))
            if s in "Yy":
                return True
            elif s in "Nn":
                return False

    @staticmethod
    def colorful(string, color):
        if platform.system().lower() == "linux":
            color_code = {
                "none": "\033[0m",
                "black": "\033[0;30m",
                "dark_gray": "\033[1;30m",
                "blue": "\033[0;34m",
                "light_blue": "\033[1;34m",
                "green": "\033[0;32m",
                "light_green": "\033[1;32m",
                "cyan": "\033[0;36m",
                "light_cyan": "\033[1;36m",
                "red": "\033[0;31m",
                "light_red": "\033[1;31m",
                "purple": "\033[0;35m",
                "light_purple": "\033[1;35m",
                "yellow": "\033[0;33m",
                "light_yellow": "\033[1;33m",
                "white": "\033[0;37m",
                "light_white": "\033[1;37m"
            }
            return color_code[color] + string + color_code["none"]
        else:
            return string

    @staticmethod
    def check_empty(check_list):
        have_err = False
        for file_name in check_list:
            if os.path.getsize(file_name) == 0:
                print(tool.colorful(file_name + " is empty", "purple"))
                have_err = True
        if have_err:
            input(tool.colorful("-----存在空文件---按回车继续-----", "yellow"))

    @staticmethod
    def readable_byte(value):
        unit = ["B", "KB", "MB", "GB"]
        level = 0
        while (value >= 1024):
            value /= 1024
            level += 1
        return "%.2f %s" % (value, unit[level])

    @staticmethod
    def download_version(arg, version):
        def download(url):
            requests.adapters.DEFAULT_RETRIES = 5  # 增加重连次数
            ses = requests.session()
            ses.keep_alive = False  # 关闭多余连接
            try:
                return ses.get(url)
            except:
                print("fail to get from :\n", "   ", url)
                exit()

        print("Warning: It will change your default config in the script.")
        print("You can use \"-config_dump\" to dump your default json.")
        input(tool.colorful("-----press enter to continue-----", "red"))
        print("Current version :", arg.version)
        print("Upgrade to :", version)
        if version == "latest":
            api_url = arg.json_data["github_url"] + "/latest"
        else:
            api_url = arg.json_data["github_url"] + "/tags/" + version
        print("Get", version, "version description from :\n" + "   ", api_url)
        version_json = download(api_url).json()
        # api_url 获取错误
        if "message" in version_json:
            print("Api message:", version_json["message"])
            print("Check the url or the version name")
            return
        # 需要更新至最新版 但已经是最新版
        if version == "latest" and version_json["tag_name"] == arg.version:
            print("Already the latest version")
            print("Use \"-get %s\" to compulsory upgrade" % arg.version)
            return
        # ignore version
        if version == "latest" and version_json["tag_name"] in arg.json_data[
                "ignore_version"]:
            print("Latest version is %s. Ignored" % version_json["tag_name"])
            return
        print("Successfully get version json, download file")
        for asset in version_json["assets"]:
            file_name = asset["name"]
            if file_name == "data_maker.py":
                file_name = arg.script_name
            else:
                while os.path.isfile(file_name):
                    file_name = "new_" + file_name
            print("Download \"%s\" and save as \"%s\"" %
                  (asset["name"], file_name))
            res = download(asset["browser_download_url"])
            with open(file_name, "wb") as fl:
                fl.write(res.content)
        print("Successfully get the version:", version)
        print("Use \"-get %s\" to back to old version" % arg.version)
        print("Version", version_json["tag_name"],
              "description:\n" + version_json["body"])


class Progress_Bar:
    def __init__(self, output_str, print_cnt=True, start_cnt=0):
        self.output_str = output_str
        self.print_cnt = print_cnt
        self.cnt = start_cnt
        self.begin()

    def begin(self):
        self.thread = threading.Thread(target=self.print_loop)
        self.thread.start()

    def print_loop(self):
        i = 0
        char = ['\\', '|', '/', '—']
        time.sleep(0.1)
        if self.print_cnt:
            while self.cnt != -1:
                print("%s:%3d %c\r" % (self.output_str, self.cnt, char[i % 4]),
                      end='')
                i += 1
                time.sleep(0.1)
        else:
            while self.cnt != -1:
                print("%s:  %c\r" % (self.output_str, char[i % 4]), end='')
                i += 1
                time.sleep(0.1)

    def increase(self):
        self.cnt += 1

    def end(self):
        self.cnt = -1
        self.thread.join()


class workflow(config):
    def __init__(self):
        config.__init__(self)

    def work(self):
        self.make_temp_dir()
        self.pre_compile()
        self.make_input_data()
        self.make_output_data()
        self.zipped()
        self.clean()
        print(tool.colorful("-----完成-----", "red"))

    def make_temp_dir(self):
        if "in" in self.option.skip:
            return
        if os.path.isdir("temp"):
            shutil.rmtree("temp")
        os.mkdir("temp")

    def pre_compile(self):
        def cpp_compile(file_name):
            file_head = os.path.splitext(file_name)[0]
            print(f"编译 {file_head}.cpp")
            message = os.popen(self.json_data["compile_cmd"]["cpp"].format(
                file_head=file_head)).read()
            # if message.count("error") != 0:
            print("%5d error" % message.count("error"))
            # if message.count("warning") != 0:
            print("%5d warning" % message.count("warning"))
            if message.count("error") > 0:
                print(tool.colorful("-----编译错误-----", "red"))
                print(message)
                exit()
            self.garbage.append(file_head + ".out")

        if self.option.input_exec_type == "cpp":
            cpp_compile(self.input_exec_name())
        if self.option.output_exec_type == "cpp":
            cpp_compile(self.output_exec_name())

    def make_input_data(self):
        if "in" in self.option.skip:
            return
        #构造数据
        if not os.path.isfile(self.input_exec_name()):
            print("\"%s\" not found" % self.input_exec_name())
            exit()
        bar = Progress_Bar("数据生成中")
        for i in range(len(self.states)):
            bar.increase()
            file_output = open(os.path.join("temp", self.input_file(i + 1)),
                               'w')
            popen = subprocess.Popen(self.input_exec().split(),
                                     stdin=subprocess.PIPE,
                                     stdout=file_output,
                                     universal_newlines=True)
            popen.stdin.write(self.states[i])
            popen.stdin.close()
            popen.wait()
            file_output.close()
        bar.end()
        print(f"数据生成完成: {len(self.states)}")
        #编辑input
        if self.option.input_edit_num >= 0:
            for i in range(self.option.input_edit_num, 0, -1):
                os.system(f"code temp/{self.input_file(i)}")
            input("-----等待更改完成---按回车继续-----")
        tool.check_empty([
            os.path.join("temp", self.input_file(i + 1))
            for i in range(len(self.states))
        ])

    def make_output_data(self):
        if "out" in self.option.skip:
            return
        if not os.path.isfile(self.output_exec_name()):
            print("\"%s\" not found" % self.output_exec_name())
            exit()
        bar = Progress_Bar("结果生成中")
        for i in range(len(self.states)):
            bar.increase()
            file_input = open(os.path.join("temp", self.input_file(i + 1)),
                              'r')
            file_output = open(os.path.join("temp", self.output_file(i + 1)),
                               'w')
            popen = subprocess.Popen(self.output_exec().split(),
                                     stdin=file_input,
                                     stdout=file_output,
                                     universal_newlines=True)
            popen.wait()
            file_input.close()
            file_output.close()
        bar.end()
        print(f"结果生成完成: {len(self.states)}")
        #check empty
        tool.check_empty([
            os.path.join("temp", self.output_file(i + 1))
            for i in range(len(self.states))
        ])
        #print output
        if self.option.output_print:
            for i in range(1, len(self.states) + 1):
                with open(os.path.join("temp", self.output_file(i)),
                          'r') as fp:
                    file_content = fp.readline()
                if len(file_content) > 50:
                    file_content = file_content[:50] + "..."
                if len(file_content) > 0 and file_content[-1] == '\n':
                    file_content = file_content[:-1]
                print("%2d: %s" % (i, file_content))
            input("-----显示结果完成---按回车继续-----")

    def zipped(self):
        if "zip" in self.option.skip:
            print(self.json_data["zip_cmd"].format(zip_name=self.option.name))
            return
        if "in_exec" in self.option.zip_file:
            shutil.copyfile(self.input_exec_name(),
                            os.path.join("temp", self.input_exec_name()))
        if "out_exec" in self.option.zip_file:
            shutil.copyfile(self.output_exec_name(),
                            os.path.join("temp", self.output_exec_name()))
        if "states" in self.option.zip_file:
            shutil.copyfile(
                self.json_data["states_name"],
                os.path.join("temp", self.json_data["states_name"]))
        zip_name = self.option.name
        if os.path.isfile(zip_name + ".zip"):
            if not tool.yesorno("是否覆盖已有Zip?(%s)" % zip_name):
                while os.path.isfile(zip_name + ".zip"):
                    zip_name = "new_" + zip_name
        bar = Progress_Bar("打包数据中", print_cnt=False)
        os.system(self.json_data["zip_cmd"].format(zip_name=zip_name))
        bar.end()
        zip_size = tool.readable_byte(os.path.getsize(zip_name + ".zip"))
        print(f"打包数据完成:  {zip_name}.zip  {zip_size}" + "\33[K")

    def clean(self, clean_temp_dir=True):
        if clean_temp_dir:
            shutil.rmtree("temp")
        for file_name in self.garbage:
            os.remove(file_name)


if __name__ == "__main__":
    try:
        work = workflow()
        work.work()
    except KeyboardInterrupt:
        try:
            work.clean(clean_temp_dir=False)
        except:
            pass
        print()