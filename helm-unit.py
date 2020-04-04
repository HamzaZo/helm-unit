import argparse
import os
from shutil import which
import subprocess  
from datetime import datetime
from ruamel.yaml import YAML
from jsonpath_ng import jsonpath, parse
import time
import sys
import glob


class HelmUnit:        
    
    def run_unit(self):
        """
        Helm Unit starter 
        """
        self.initialize_arg_parser()
        self.validator_pre_check()
        
    def initialize_arg_parser(self):
        """
        Create helm unit cli
        
        :return: args_cli
        """
        
        self.arg_parser = argparse.ArgumentParser(description='Run unit-test on chart locally without deloying the release.',prog='helm unit',usage='%(prog)s [CHART-DIR] [TEST-DIR]')
        self.arg_parser.add_argument('--chart',dest='chart',type=str,required=True,help='Specify chart directory')
        self.arg_parser.add_argument('--tests',dest='tests',type=str,required=True,help='Specify Unit tests directory')
        self.arg_parser.add_argument('--version',action='version',version='BuildInfo{Timestamp:' + str(datetime.now())+ ', version: 0.1.0-alpha}',help='Print version information')
        try:
            self.args_cli = self.arg_parser.parse_args()
            self.chart = self.args_cli.chart
            self.tests = self.args_cli.tests
            return self.args_cli
        except IOError as err:
            self.arg_parser.error(str(err))
              
    
    def validator_pre_check(self):
        """
        Validate cli prerequisites 
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
            
        try:
            version = subprocess.Popen(['helm', 'version','--short'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out,err = version.communicate()
            output=out.decode('utf-8').split('+')
            if which('helm') and output[0].startswith('v3'):
                print('✔️ Detecting Helm 3 : PASS 🎯\n')
            else:
                print('❌ You are using an old version of Helm binary, the plugin support only Helm 3')
                sys.exit(1)
        except ValueError as err:
            print('❌ Unable to find a valid executable Helm binary :: {}'.format(err))
            sys.exit(1)
            
        
class Linter(HelmUnit):
    def __init__(self):
        super().__init__()
        
    
    def linting_chart(self):
        """
        Chart syntax validator 
        """
        try:
            self.run_unit()
            if "templates" in os.listdir(self.chart): 
                print('✔️ Validating chart syntax..⏳\n')
                time.sleep(1)
                check_syntax = subprocess.Popen(['helm', 'lint', self.chart], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
  

class UnitTest(Linter):
    def __init__(self):
        super().__init__()
            
    def render_chart(self):
        """
        Render chart templates locally.
        """
        self.linting_chart()
        try:
            release = subprocess.Popen(['helm', 'template', 'tmp', self.chart, '--validate', '--is-upgrade'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
     
  
     
     
    def run_test(self):
        """
        Running Unit test on helm chart templates.
        """
        self.render_chart()
        for file_name,file_test in self.dic_tests.items():
            print('---> Applying\033[1m {}\033[0m file..⏳\n'.format(file_name))
            time.sleep(1)
            kind_type = parse('$.tests[0].type').find(file_test)
            kind_name = parse('$.tests[0].name').find(file_test)
            print('==> Running Tests on\033[1;36;10m {} {}\033[0m ..\n'.format(kind_name[0].value,kind_type[0].value))
            time.sleep(1)
            test_scenario = parse('$..asserts[*]').find(file_test)
            
            chartToTest = ''
            try:
                chartToTest = self.mydict[kind_type[0].value][kind_name[0].value]
            except Exception as err:
                print('❌ {} with name {} does not exist in chart {} - testing failed '.format(kind_type[0].value, kind_name[0].value, self.chart))
                print('For {} object found {} as names - Make sure you are using the right name!'.format(kind_type[0].value, [key for key in self.mydict[kind_type[0].value] ]))
                continue
            
            try:
                for k in test_scenario:
                    for item in k.value['values']:
                        find_spec = parse('$.' + item['path']).find(chartToTest)
                        if len(find_spec) == 0:  
                            print('❌ Errors : Could not find expected {} in templates \n'.format(item['path']))
                            break
                        if k.value['type'] == 'equal':
                            if find_spec[0].value is not None and find_spec[0].value == item['value']:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                        elif k.value['type'] == 'notEqual':
                            if find_spec[0].value is not None and find_spec[0].value != item['value']:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                        elif k.value['type'] == 'contains':
                            content_Array = [match.value for match in parse('$.'+ item['path']).find(chartToTest)]
                            if item['value'] in content_Array:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                        elif k.value['type'] == 'isNotEmpty':
                            if find_spec[0].value is not None and len(find_spec[0].value) > 0:
                                print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                            else:
                                print('❌ {} : FAILED \n'.format(k.value['name']))
                        else:
                            print('❌ Unrecognized type {}  \n'.format(k.value['type']))
                    
            except Exception as err:
                print('❌ testing {} chart templates failed :: {}'.format(err,self.chart))
       
            
        
if __name__ == "__main__":
    yaml = YAML()
    chart = UnitTest()
    chart.run_test()
    print('🕸 Happy Helming testing day! 🕸')
    
    