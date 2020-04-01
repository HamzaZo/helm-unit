import argparse
import os
from shutil import which
import subprocess  
from datetime import datetime
from ruamel.yaml import YAML
from jsonpath_ng import jsonpath, parse
import time
import sys



class HelmUnit:
    def __init__(self):
        self.initialize_arg_parser()
        self.check_helm_version()
        
    def initialize_arg_parser(self):
        """
        Create helm unit cli plugin
        """
        
        self.arg_parser = argparse.ArgumentParser(description='The Helm TestUnit plugin runs tests on a chart locally without deloying the release.',prog='helm unit',usage='%(prog)s [CHART-DIR] [TEST-FILE]')
        self.arg_parser.add_argument('--chart',dest='dir',type=str,required=True,help='Specify chart directory')
        self.arg_parser.add_argument('--test',dest='file',type=argparse.FileType('r'),required=True,help='Specify Test Unit in a YAML file')
        self.arg_parser.add_argument('--version',action='version',version='BuildInfo{Timestamp:' + str(datetime.now())+ ', version: 0.1.0-alpha}',help='Print version information')
        try:
            self.args_cli = self.arg_parser.parse_args()
            self.dir = self.args_cli.dir
            self.file = self.args_cli.file
            return self.args_cli
        except IOError as err:
            self.arg_parser.error(str(err))
                
    
    def check_helm_version(self):
        """
        Verify Helm version 
        """
        try:
            self.version = subprocess.Popen(['helm', 'version','--short'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.out,self.err = self.version.communicate()
            self.output=self.out.decode('utf-8').split('+')
            if which('helm') and self.output[0].startswith('v3'):
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
        Validator of helm chart syntax 
        """
        try:
            self.initialize_arg_parser()
            if "templates" in os.listdir(self.dir): 
                print('✔️ Checking chart syntax..⏳\n')
                time.sleep(1)
                self.check_syntax = subprocess.Popen(['helm', 'lint', self.dir], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                self.out_syn,self.out_err = self.check_syntax.communicate()
                if self.check_syntax.returncode == 0:
                    msg = self.out_syn.decode('utf-8').replace('[INFO] Chart.yaml: icon is recommended','PASS 🎯').replace('1 chart(s) linted, 0 chart(s) failed','').strip() 
                    print('{} \n'.format(msg))
                else: 
                    msg = self.out_syn.decode('utf-8').replace('[INFO] Chart.yaml: icon is recommended','').replace('Error: 1 chart(s) linted, 1 chart(s) failed','').strip()
                    print('❌ {} \n'.format(msg))
                    sys.exit(1) 
            else:  
                print('❌ Could not find templates in {} chart'.format(self.dir))
                sys.exit(1) 
        except Exception as err:
            print('❌ Failed to find a chart - linting failed :: {}'.format(err))
            
            
                 
class UnitTest(Linter):
    def __init__(self):
        super().__init__()
    
    def render_chart(self):
        """
        Validate and Render chart templates locally and store it into a dict.
        """
        self.linting_chart()
        kinds = []
        try:
            self.release = subprocess.Popen(['helm', 'template', 'tmp', self.dir, '--validate', '--is-upgrade'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.out_rel,self.err_rel = self.release.communicate()
            self.output = self.out_rel.decode('utf-8')
            self.split_manifests = self.output.split('---')
            if self.release.returncode == 0:
                for k in self.split_manifests:
                    self.chart_templates = yaml.load(k)
                    if self.chart_templates is not None:
                        if self.chart_templates['kind'] not in kinds:
                            kinds.append(self.chart_templates['kind'])
                        
                self.mydict = dict.fromkeys(kinds,{})
                for k in self.split_manifests:
                    self.chart_templates = yaml.load(k)
                    if self.chart_templates is not None:
                        self.metadata = self.chart_templates['metadata']['name']
                        self.find_spec_value = parse('$[*]').find(self.chart_templates)
                        self.mydict[self.chart_templates['kind']][self.metadata] = self.find_spec_value[0].value
            else:
                print(' ❌ {} '.format(self.out_rel.decode('utf-8')))
                sys.exit(1)
        except Exception as err:
            print('❌ rendering {} chart templates failed :: {}'.format(err,self.dir))             
    
    def run_test(self):
        """
        Running Unit test on helm chart templates
        """
        self.render_chart()        
        self.test_file = yaml.load(self.file)
        self.kind_type = parse('$.tests[0].type').find(self.test_file)
        self.kind_name = parse('$.tests[0].name').find(self.test_file)
        print('==> Running Tests on {} {}..⏳\n'.format(self.kind_name[0].value,self.kind_type[0].value))
        time.sleep(1)
        self.test_scenario = parse('$..asserts[*]').find(self.test_file)
        try:
            for k in self.test_scenario:
                for item in k.value['values']:
                    self.find_spec = parse('$.' + item['path']).find(self.mydict[self.kind_type[0].value][self.kind_name[0].value])
                    if len(self.find_spec) == 0:  
                        print('❌ Errors : Could not find expected {} in templates \n'.format(item['path']))
                        break
                    if k.value['type'] == 'equal':
                        if self.find_spec[0].value is not None and self.find_spec[0].value == item['value']:
                            print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                        else:
                            print('❌ {} : FAILED \n'.format(k.value['name']))
                    elif k.value['type'] == 'notEqual':
                        if self.find_spec[0].value is not None and self.find_spec[0].value != item['value']:
                            print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                        else:
                            print('❌ {} : FAILED \n'.format(k.value['name']))
                    elif k.value['type'] == 'contains':
                        self.content_Array = [match.value for match in parse('$.'+ item['path']).find(self.mydict[self.kind_type[0].value][self.kind_name[0].value])]
                        if item['value'] in self.content_Array:
                            print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                        else:
                            print('❌ {} : FAILED \n'.format(k.value['name']))
                    elif k.value['type'] == 'isNotEmpty':
                        if self.find_spec[0].value is not None and len(self.find_spec[0].value) > 0:
                            print('✔️ {} : PASS 🎯\n'.format(k.value['name']))
                        else:
                            print('❌ {} : FAILED \n'.format(k.value['name']))
                    else:
                        print('❌ Unrecognized type {}  \n'.format(k.value['type']))
                    
        except Exception as err:
            print('❌ testing {} chart templates failed :: {}'.format(err,self.dir))
               
               
            
if __name__ == "__main__":
    yaml = YAML()
    chart = UnitTest()
    chart.run_test()
    print('Happy Helming testing day!')
    
    