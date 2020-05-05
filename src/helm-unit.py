import argparse
import os
import subprocess
from datetime import datetime
from ruamel.yaml import YAML
from jsonpath_ng import parse
import time
import sys
import glob
from ruamel.yaml.compat import StringIO
import re


class Unit:
    def initialize_unit(self):
        """
        Helm Unit Initializer
        """
        self.initialize_arg_parser()
        check_version()
        self.tests_loader()

    def initialize_arg_parser(self):
        """
        Create helm unit cli
        :return: args_cli
        """
        self.arg_parser = argparse.ArgumentParser(
            description='Run unit-test on chart locally without deploying the release.', prog='helm unit',
            usage='%(prog)s [CHART-DIR] [TEST-DIR]')
        self.arg_parser.add_argument('--chart', metavar='CHART-PATH', dest='chart', type=str, required=True,
                                     help='Specify chart directory')
        self.arg_parser.add_argument('--tests', metavar='TESTS-PATH', dest='tests', type=str, required=True,
                                     help='Specify Unit tests directory')
        self.arg_parser.add_argument('--version', action='version',
                                     version='BuildInfo{Timestamp:' + str(datetime.now()) + ', version: 0.1.5}',
                                     help='Print version information')
        try:
            self.args_cli = self.arg_parser.parse_args()
            self.chart = self.args_cli.chart
            self.tests = self.args_cli.tests
            return self.args_cli
        except IOError as err:
            self.arg_parser.error(str(err))

    def tests_loader(self):
        """
        Load Unit Tests from directory.
        """
        try:
            if os.path.exists(self.tests) and os.path.isdir(self.tests):
                if os.listdir(self.tests):
                    files = glob.glob(self.tests + '/*.yaml')
                    self.dic_tests = {}
                    for file_name in files:
                        with open(file_name, 'r') as stream:
                            test_content = yaml.load(stream)
                        self.dic_tests[file_name.replace(self.tests + '/', '')] = test_content
                else:
                    print(' {} No yaml test file was found in {} directory'.format(
                        self.tests, str("\033[1;31;10m X \033[0m")))
                    sys.exit(1)
            else:
                print(" {} {} directory  does not exists".format(
                    self.tests, str("\033[1;31;10m X \033[0m")))
                sys.exit(1)
        except Exception as err:
            print('{} {}'.format(err, str("\033[1;31;10m X \033[""0m")))
            sys.exit(1)


def check_version():
    """
    Validate helm binary version.
    """
    try:
        version = subprocess.Popen(['helm', 'version', '--short'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = version.communicate()
        output = str(out, 'utf-8').split('+')
        compatibility_version = output[0].split('.')[1]
        if output[0].startswith('v3'):
            if int(compatibility_version) > 0:
                print('√ Detecting Helm 3 : {} \n'.format(
                    str("\033[1;32;10m PASS \033[0m")))
            else:
                print('{} You are using an incompatible version, '
                      'see https://github.com/HamzaZo/helm-unit#prerequisite'.format(
                       str("\033[1;31;10m X \033[0m")))
                sys.exit(1)
    except ValueError as erv:
        print('{} Unable to find a supported helm version :: {}'.format(
            erv, str("\033[1;31;10m X \033[""0m")))
        sys.exit(1)


class Linting(Unit):
    def __init__(self):
        super().__init__()

    def linting_chart(self):
        """
        Chart syntax validator
        """
        try:
            self.initialize_unit()
            if "templates" in os.listdir(self.chart):
                print('√ Validating chart syntax..\n')
                time.sleep(1)
                check_syntax = subprocess.Popen(['helm', 'lint', self.chart], stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                out_syn, out_err = check_syntax.communicate()
                if check_syntax.returncode == 0:
                    msg = str(out_syn, 'utf-8').replace('[INFO] Chart.yaml: icon is recommended',
                                                        str("\033[1;32;10m PASS \033[0m")).replace(
                        '1 chart(s) linted, 0 chart(s) failed', '').strip()
                    print('{} \n'.format(msg))
                else:
                    msg = str(out_syn, 'utf-8').replace('[INFO] Chart.yaml: icon is recommended', '').replace(
                        'Error: 1 chart(s) linted, 1 chart(s) failed', '').strip()
                    print('{} {} \n'.format(msg, str("\033[1;31;10m X \033[0m")))
                    sys.exit(1)
            else:
                print('{} Could not find templates in {} chart'.format(
                    self.chart, str("\033[1;31;10m X \033[0m")))
                sys.exit(1)
        except Exception as err:
            print('{} Failed to find a chart - linting failed :: {}'.format(
                err, str("\033[1;31;10m X \033[0m")))
            sys.exit(1)


def assert_pre_check(asserts_test, kind_name):
    """
    validate asserts
    :return: bool
    """
    match_types = {
        "equal": ["path", "value"],
        "notEqual": ["path", "value"],
        "contains": ["path", "value"],
        "notContains": ["path", "value"],
        "matchValue": ["path", "pattern"],
        "notMatchValue": ["path", "pattern"],
        "isEmpty": ["path"],
        "isNotEmpty": ["path"]
    }

    if 'type' not in asserts_test.value:
        print(
            '{}Test: {} does not have an assert type'.format(
                str("\033[1;31;10m X \033[0m"),
                str("\033[1;31;10m" + kind_name + "\033[0m")))
        return False
    if 'values' not in asserts_test.value:
        print('{}Test: {} does not have an assert values'.format(
            str("\033[1;31;10m X \033[0m"),
            str("\033[1;31;10m" + kind_name + "\033[0m")))
        return False
    if asserts_test.value['type'] in match_types:
        for match_item in match_types[asserts_test.value['type']]:
            for item in asserts_test.value['values']:
                if match_item not in item:
                    print(
                        '{}Test: {} does not have {} in assert type'.format(
                            str("\033[1;31;10m X ""\033[""0m"),
                            str("\033[1;31;10m" + kind_name + " \033[0m"),
                            str("\033[1;31;10m" + match_item + "\033[0m")))
                    return False
                for val in item:
                    if val not in match_types[asserts_test.value['type']]:
                        print('{}Test: {} contains unsupported value {} - We only support {} '.format(
                            str("\033[1;31;10m X ""\033[""0m"),
                            str("\033[1;31;10m" + kind_name + "\033[0m"),
                            str("\033[1;31;10m" + val + "\033[0m"), match_types[asserts_test.value['type']]))
                        return False
    return True


class YamlDump(YAML):
    """
    Dump a YAML element, to take it as string and not to interpret the content of data.
    """

    def dump(self, data, stream=None, **kw):
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if inefficient:
            return stream.getvalue()


class Testing(Linting):
    def __init__(self):
        super().__init__()

    def render_chart(self):
        """
        Render chart templates locally.
        """
        self.linting_chart()
        try:
            release = subprocess.Popen(['helm', 'template', 'tmp', self.chart, '--validate', '--is-upgrade'],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out_rel, err_rel = release.communicate()
            output = str(out_rel, 'utf-8')
            split_manifests = output.split('---')
            self.mydict = {}
            if release.returncode == 0:
                for k in split_manifests:
                    chart_templates = yaml.load(k)
                    if chart_templates is not None:
                        if chart_templates['kind'] not in self.mydict:
                            self.mydict[chart_templates['kind']] = {}

                for k in split_manifests:
                    chart_templates = yaml.load(k)
                    if chart_templates is not None:
                        metadata = chart_templates['metadata']['name']
                        find_spec_value = parse('$[*]').find(chart_templates)
                        self.mydict[chart_templates['kind']][metadata] = find_spec_value[0].value
            else:
                print(' {} {} '.format(
                    str(out_rel, 'utf-8'), str("\033[1;31;10m X \033[""0m")))
                sys.exit(1)

        except Exception as err:
            print('{} rendering {} chart templates failed :: {}'.format(
                err, self.chart, str("\033[1;31;10m X \033[""0m")))
            sys.exit(1)

    def run_test(self):
        """
        Running test on chart templates.
        """
        self.render_chart()
        msg = ''
        for file_name, file_test in self.dic_tests.items():
            print('---> Applying {} file..\n'.format(
                str("\033[1m" + file_name + "\033[0m")))
            time.sleep(1)
            kind_type = parse('$.tests[0].type').find(file_test)
            kind_name = parse('$.tests[0].name').find(file_test)
            print('==> Running Tests on {} {}..\n'.format(
                str("\033[1m" + kind_name[0].value + "\033[0m"),
                str("\033[1m" + kind_type[0].value + "\033[0m")))
            time.sleep(1)
            test_scenario = parse('$..asserts[*]').find(file_test)

            chart_to_test = ''
            try:
                chart_to_test = self.mydict[kind_type[0].value][kind_name[0].value]

            except Exception:
                print(
                    ' {} {} kind with name {} does not exist in {} chart - Testing Failed '.format(
                        str("\033[1;31;10m X \033[0m"), kind_type[0].value, kind_name[0].value, self.chart))
                print('Found {} as names for kind {}  - Make sure you are using the right name!'.format(
                    [key for key in self.mydict[kind_type[0].value]], kind_type[0].value))
                continue

            try:
                test_ok = 0
                test_ko = 0
                for k in test_scenario:
                    check_test_syntax = assert_pre_check(k, k.value['name'])
                    if not check_test_syntax:
                        continue
                    for item in k.value['values']:
                        find_spec = parse('$.' + item['path']).find(chart_to_test)
                        if len(find_spec) == 0:
                            print(
                                '{} ERROR: Could not find expected {} in {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), item['path'], k.value['name']))
                            test_ko += 1
                            break
                        if k.value['type'] == 'equal':
                            if find_spec[0].value is not None and find_spec[0].value == item['value']:
                                print('√ {} : {}\n'.format(
                                    k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                test_ok += 1
                            else:
                                print('{} {} : {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), k.value['name'],
                                    str("\033[1;31;10m FAILED \033[0m")))
                                test_ko += 1
                        elif k.value['type'] == 'notEqual':
                            if find_spec[0].value is not None and find_spec[0].value != item['value']:
                                print('√ {} : {}\n'.format(
                                    k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                test_ok += 1
                            else:
                                print('{} {} : {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), k.value['name'],
                                    str("\033[1;31;10m FAILED \033[0m")))
                                test_ko += 1
                        elif k.value['type'] == 'contains':
                            type_item_value = type(item['value'])
                            if type_item_value is str:
                                self.content_array = [match.value for match in
                                                      parse('$.' + item['path']).find(chart_to_test)]
                                if item['value'] in self.content_array:
                                    print('√ {} : {}\n'.format(
                                        k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                    test_ok += 1
                                else:
                                    print('{} {} : {} \n'.format(
                                        str("\033[1;31;10m X \033[0m"), k.value['name'],
                                        str("\033[1;31;10m FAILED \033[0m")))
                                    test_ko += 1
                            else:
                                dump_yaml = YamlDump()
                                values_to_test = dump_yaml.dump(
                                    parse('$.' + item['path']).find(chart_to_test)[0].value).split('\n')
                                value_size = len(item['value'])
                                for index in range(value_size):
                                    if item['value'][index] in values_to_test:
                                        print('√ {} {}: {} \n'.format(
                                            k.value['name'], item['value'][index], str("\033[1;32;10m PASS \033[0m")))
                                        test_ok += 1
                                    else:
                                        print('{} {} {} : {} \n'.format(
                                            str("\033[1;31;10m X \033[0m"), k.value['name'], item['value'][index],
                                            str("\033[1;31;10m FAILED \033[0m")))
                                        test_ko += 1
                        elif k.value['type'] == 'notContains':
                            type_item_value = type(item['value'])
                            if type_item_value is str:
                                self.content_array = [match.value for match in
                                                      parse('$.' + item['path']).find(chart_to_test)]
                                if item['value'] not in self.content_array:
                                    print('√ {} : {}\n'.format(
                                        k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                    test_ok += 1
                                else:
                                    print('{} {} : {} \n'.format(
                                        str("\033[1;31;10m X \033[0m"), k.value['name'],
                                        str("\033[1;31;10m FAILED \033[0m")))
                                    test_ko += 1
                            else:
                                dump_yaml = YamlDump()
                                values_to_test = dump_yaml.dump(
                                    parse('$.' + item['path']).find(chart_to_test)[0].value).split('\n')
                                value_size = len(item['value'])
                                for index in range(value_size):
                                    if item['value'][index] not in values_to_test:
                                        print('√ {} {}: {} \n'.format(
                                            k.value['name'], item['value'][index], str("\033[1;32;10m PASS \033[0m")))
                                        test_ok += 1
                                    else:
                                        print('{} {} {} : {} \n'.format(
                                            str("\033[1;31;10m X \033[0m"), k.value['name'], item['value'][index],
                                            str("\033[1;31;10m FAILED \033[0m")))
                                        test_ko += 1
                        elif k.value['type'] == 'isNotEmpty':
                            if find_spec[0].value is not None and len(find_spec[0].value) > 0:
                                print('√ {} : {}\n'.format(
                                    k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                test_ok += 1
                            else:
                                print('{} {} : {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), k.value['name'],
                                    str("\033[1;31;10m FAILED \033[0m")))
                                test_ko += 1
                        elif k.value['type'] == 'isEmpty':
                            if len(find_spec[0].value) == 0:
                                print('√ {} : {}\n'.format(
                                    k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                test_ok += 1
                            else:
                                print('{} {} : {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), k.value['name'],
                                    str("\033[1;31;10m FAILED \033[0m")))
                                test_ko += 1
                        elif k.value['type'] == 'matchValue':
                            value_to_match = re.search(item['pattern'], find_spec[0].value)
                            if value_to_match and value_to_match is not None:
                                print('√ {} : {}\n'.format(
                                    k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                test_ok += 1
                            else:
                                print('{} {} : {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), k.value['name'],
                                    str("\033[1;31;10m FAILED \033[0m")))
                                test_ko += 1
                        elif k.value['type'] == 'notMatchValue':
                            value_to_match = re.search(item['pattern'], find_spec[0].value)
                            if not value_to_match and value_to_match is None:
                                print('√ {} : {}\n'.format(
                                    k.value['name'], str("\033[1;32;10m PASS \033[0m")))
                                test_ok += 1
                            else:
                                print('{} {} : {} \n'.format(
                                    str("\033[1;31;10m X \033[0m"), k.value['name'],
                                    str("\033[1;31;10m FAILED \033[0m")))
                                test_ko += 1
                        else:
                            print('{} Unrecognized type {}  \n'.format(
                                k.value['type'], str("\033[1;31;10m X \033[0m")))

            except Exception as err:
                print('{} Testing {}  :: {} failed'.format(
                    str("\033[1;31;10m X \033[0m"), err, self.chart))

            start_failed_color = str("\033[1;31;10m")
            start_success_color = str("\033[1;32;10m")
            end_color = str("\033[0m")

            if test_ok > 0 and test_ko == 0:
                test_color = start_success_color + file_name + end_color
            else:
                test_color = start_failed_color + file_name + end_color

            msg += test_color + '\n' + 'Number of executed tests : ' + str(
                test_ok + test_ko) + '\n' + 'Number of success tests : ' + str(
                test_ok) + '\n' + 'Number of failed tests : ' + str(test_ko) + '\n\n'
        print('{} \n'.format(str("\033[1;34;10m==> Unit Tests Summary\033[0m:")))
        print(msg)


if __name__ == "__main__":
    yaml = YAML()
    chart = Testing()
    chart.run_test()
    print('+-------------------------+ '
          'Happy Helming testing day! '
          '+-------------------------+'
          '')
