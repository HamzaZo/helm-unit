import argparse
import os
from shutil import which
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
        self.check_version()
        self.tests_loader()

    def initialize_arg_parser(self):
        """
        Create helm unit cli
        :return: args_cli
        """
        self.arg_parser = argparse.ArgumentParser(
            description='Run unit-test on chart locally without deloying the release.', prog='helm unit',
            usage='%(prog)s [CHART-DIR] [TEST-DIR]')
        self.arg_parser.add_argument('--chart', metavar='CHART-PATH', dest='chart', type=str, required=True,
                                     help='Specify chart directory')
        self.arg_parser.add_argument('--tests', metavar='TESTS-PATH', dest='tests', type=str, required=True,
                                     help='Specify Unit tests directory')
        self.arg_parser.add_argument('--version', action='version',
                                     version='BuildInfo{Timestamp:' + str(datetime.now()) + ', version: 0.1.2}',
                                     help='Print version information')
        try:
            self.args_cli = self.arg_parser.parse_args()
            self.chart = self.args_cli.chart
            self.tests = self.args_cli.tests
            return self.args_cli
        except IOError as err:
            self.arg_parser.error(str(err))
    
    def check_version(self):
        """
        Validate helm binary version.
        """
        try:
            version = subprocess.Popen(['helm', 'version','--short'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out,err = version.communicate()
            output=out.decode('utf-8').split('+')
            compatibility_version = output[0].split('.')[1]
            if which('helm') and output[0].startswith('v3'):
                if int(compatibility_version) > 0:
                    print('✔️ Detecting Helm 3 : PASS 🎯\n')
                else:
                    print('❌ You are using an incompatible version, see https://github.com/HamzaZo/helm-unit#prerequisite')
                    sys.exit(1)
        except ValueError as errv:
            print('❌ Unable to find a supported helm version :: {}'.format(errv))
            sys.exit(1)
            
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
                        self.dic_tests[file_name.replace(self.tests +'/', '')] = test_content
                else:
                    print(' ❌ No yaml test file was found in {} directory'.format(self.tests))
                    sys.exit(1)
            else:
                print(" ❌ {} directory  does not exists".format(self.tests))
                sys.exit(1)
        except Exception as err:
            print('❌ {}'.format(err))
            sys.exit(1)
        
class ChartLinter(Unit):
    def __init__(self):
        super().__init__()
        
    def linting_chart(self):
        """
        Chart syntax validator 
        """
        try:
            self.initialize_unit()
            if "templates" in os.listdir(self.chart): 
                print('✔️ Validating chart syntax..⏳\n')
                time.sleep(1)
                check_syntax = subprocess.Popen(['helm', 'lint', self.chart], stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT)
                out_syn,out_err = check_syntax.communicate()
                if check_syntax.returncode == 0:
                    msg = out_syn.decode('utf-8').replace('[INFO] Chart.yaml: icon is recommended','PASS 🎯').replace('1 chart(s) linted, 0 chart(s) failed','').strip() 
                    print('{} \n'.format(msg))
                else: 
                    msg = out_syn.decode('utf-8').replace('[INFO] Chart.yaml: icon is recommended','').replace('Error: 1 chart(s) linted, 1 chart(s) failed','').strip()
                    print('❌ {} \n'.format(msg))
                    sys.exit(1) 
            else:  
                print('❌ Could not find templates in {} chart'.format(self.chart))
                sys.exit(1) 
        except Exception as err:
            print('❌ Failed to find a chart - linting failed :: {}'.format(err))
            sys.exit(1)



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


class ChartTester(ChartLinter):
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
            out_rel,err_rel = release.communicate()
            output = out_rel.decode('utf-8')
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
                print(' ❌ {} '.format(out_rel.decode('utf-8')))
                sys.exit(1)
        except Exception as err:
            print('❌ rendering {} chart templates failed :: {}'.format(err,self.chart))
            sys.exit(1)

    @staticmethod
    def assert_pre_check(asserts_test,kind_name):
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
            print('❌  Test: \033[1;31;10m {} \033[0m does not have an assert type'.format(kind_name))
            return False
        if 'values' not in asserts_test.value:
            print('❌  Test: \033[1;31;10m {} \033[0m does not have an assert values'.format(kind_name))
            return False
        if asserts_test.value['type'] in match_types:
            for match_item in match_types[asserts_test.value['type']]:
                for item in asserts_test.value['values']:
                    if match_item not in item:
                        print(
                            '❌  Test: \033[1;31;10m {} \033[0m does not have \033[1;31;10m{}\033[0m in assert type'.format(
                                kind_name, match_item))
                        return False
                    for val in item :
                        if val not in match_types[asserts_test.value['type']]:
                            print('❌  Test: \033[1;31;10m {} \033[0m contains unsupported value \033[1;31;10m {} '
                                  '\033[0m - We only support {} '.format(kind_name,val,match_types[
                                asserts_test.value['type']]))
                            return False
        return True


    def run_test(self):
        """
        Running test on chart templates.
        """
        self.render_chart()
        msg = ''
        for file_name,file_test in self.dic_tests.items():
            print('---> Applying\033[1m {}\033[0m file..⏳\n'.format(file_name))
            time.sleep(1)
            kind_type = parse('$.tests[0].type').find(file_test)
            kind_name = parse('$.tests[0].name').find(file_test)
            print('==> Running Tests on\033[1;36;10m {} {}\033[0m ..\n'.format(kind_name[0].value, kind_type[0].value))
            time.sleep(1)
            test_scenario = parse('$..asserts[*]').find(file_test)

            chartToTest = ''
            try:
                chartToTest = self.mydict[kind_type[0].value][kind_name[0].value]
            except Exception as err:
                print('❌ {} kind with name {} does not exist in chart {} - testing failed '.format(kind_type[0].value,
                                                                                                   kind_name[0].value,
                                                                                                   self.chart))
                print('Found {} as names for kind {}  - Make sure you are using the right name!'.format(
                    [key for key in self.mydict[kind_type[0].value]], kind_type[0].value))
                continue

            try:
                test_ok = 0
                test_ko = 0
                for k in test_scenario:
                    check_test_syntax = self.assert_pre_check(k, k.value['name'])
                    if not check_test_syntax:
                        continue
                    for item in k.value['values']:
                        find_spec = parse('$.' + item['path']).find(chartToTest)
                        if len(find_spec) == 0:
                            print(
                                '❌ Errors : Could not find expected {} in {} \n'.format(item['path'], k.value['name']))
                            test_ko += 1
                            break
                        if k.value['type'] == 'equal':
                            if find_spec[0].value is not None and find_spec[0].value == item['value']:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                test_ok += 1
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                                test_ko += 1
                        elif k.value['type'] == 'notEqual':
                            if find_spec[0].value is not None and find_spec[0].value != item['value']:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                test_ok += 1
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                                test_ko += 1
                        elif k.value['type'] == 'contains':
                            typeItemval = type(item['value'])
                            if typeItemval is str:
                                self.content_Array = [match.value for match in parse('$.'+ item['path']).find(chartToTest)]
                                if item['value'] in self.content_Array:
                                    print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                    test_ok += 1
                                else:
                                    print('❌ {} : FAILED \n'.format(k.value['name']))
                                    test_ko += 1
                            else:
                                yamldump = YamlDump()
                                valuesToTest = yamldump.dump(parse('$.'+ item['path']).find(chartToTest)[0].value).split('\n')
                                sizeVal = len(item['value'])
                                for indexVal in range(sizeVal):
                                    if item['value'][indexVal] in valuesToTest:
                                        print('✔️ {} {}: PASS 🎯\n'.format(k.value['name'],item['value'][indexVal]))
                                        test_ok += 1
                                    else:
                                        print('❌ {} {} : FAILED \n'.format(k.value['name'],item['value'][indexVal]))
                                        test_ko += 1
                        elif k.value['type'] == 'notContains':
                            typeItemval = type(item['value'])
                            if typeItemval is str:
                                self.content_Array = [match.value for match in parse('$.'+ item['path']).find(chartToTest)]
                                if item['value'] not in self.content_Array:
                                    print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                    test_ok += 1
                                else:
                                    print('❌ {} : FAILED \n'.format(k.value['name']))
                                    test_ko += 1
                            else:
                                yamldump = YamlDump()
                                valuesToTest = yamldump.dump(parse('$.'+ item['path']).find(chartToTest)[0].value).split('\n')
                                sizeVal = len(item['value'])
                                for indexVal in range(sizeVal):
                                    if item['value'][indexVal] not in valuesToTest:
                                        print('✔️ {} {}: PASS 🎯\n'.format(k.value['name'],item['value'][indexVal]))
                                        test_ok += 1
                                    else:
                                        print('❌ {} {} : FAILED \n'.format(k.value['name'],item['value'][indexVal]))
                                        test_ko += 1
                        elif k.value['type'] == 'isNotEmpty':
                            if find_spec[0].value is not None and len(find_spec[0].value) > 0:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                test_ok += 1
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                                test_ko += 1
                        elif k.value['type'] == 'isEmpty':
                            if len(find_spec[0].value) == 0:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                test_ok += 1
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                                test_ko += 1
                        elif k.value['type'] == 'matchValue':
                            value_to_match = re.search(item['pattern'], find_spec[0].value)
                            if value_to_match and value_to_match is not None:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                test_ok += 1
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                                test_ko += 1
                        elif k.value['type'] == 'notMatchValue':
                            value_to_match = re.search(item['pattern'], find_spec[0].value)
                            if not value_to_match and value_to_match is None:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                                test_ok += 1
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                                test_ko += 1
                        else:
                            print('❌ Unrecognized type {}  \n'.format(k.value['type']))
                    
            except Exception as err:
                print('❌ Testing {}  :: {} failed'.format(err,self.chart))
            
            start_failed_color = '\033[1;31;10m'
            start_success_color = '\033[1;32;10m'
            end_color  = ' \033[0m '
            
            if test_ok > 0 and test_ko == 0:
                test_color = start_success_color + file_name + end_color
            else:
                test_color = start_failed_color + file_name + end_color

            msg += test_color + '\n' + 'Number of executed tests : ' + str(
                test_ok + test_ko) + '\n' + 'Number of success tests : ' + str(
                test_ok) + '\n' + 'Number of failed tests : ' + str(test_ko) + '\n\n'
        print('\033[1;34;10m==> Unit Tests Summary\033[0m:\n')
        print(msg)
            
        
if __name__ == "__main__":
    yaml = YAML()
    chart = ChartTester()
    chart.run_test()
    print('🕸  Happy Helming testing day! 🕸')