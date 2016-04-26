from Tester import Tester
from CSVDiffer import CSVDiffer
from UnorderedCSVDiffer import UnorderedCSVDiffer
from XMLDiff import XMLDiff
import RavenUtils
import os
import subprocess
import sys

# Set this outside the class because the framework directory is constant for
#  each instance of this Tester, and in addition, there is a problem with the
#  path by the time you call it in __init__ that causes it to think its absolute
#  path is somewhere under tests/framework.
# Be aware that if this file changes its location, this variable should also be
#  changed.
myDir = os.path.dirname(os.path.realpath(__file__))
RAVEN_DIR = os.path.abspath(os.path.join(myDir, '..', '..', '..', 'framework'))

_missing_modules, _too_old_modules, _notQAModules = RavenUtils.checkForMissingModules()

class RavenFramework(Tester):

  @staticmethod
  def validParams():
    params = Tester.validParams()
    params.addRequiredParam('input',"The input file to use for this test.")
    params.addParam('output','',"List of output files that the input should create.")
    params.addParam('csv','',"List of csv files to check")
    params.addParam('UnorderedCsv','',"List of unordered csv files to check")
    params.addParam('xml','',"List of xml files to check")
    params.addParam('UnorderedXml','',"List of unordered xml files to check")
    params.addParam('xmlopts','',"Options for xml checking")
    params.addParam('rel_err','','Relative Error for csv files or floats in xml ones')
    params.addParam('required_executable','','Skip test if this executable is not found')
    params.addParam('required_libraries','','Skip test if any of these libraries are not found')
    params.addParam('skip_if_env','','Skip test if this environmental variable is defined')
    params.addParam('test_interface_only','False','Test the interface only (without running the driven code')
    params.addParam('zero_threshold',sys.float_info.min*4.0,'it represents the value below which a float is considered zero (XML comparison only)')
    params.addParam('remove_whitespace','False','Removes whitespace before comparing xml node text if True')
    params.addParam('expected_fail', 'False', 'if true, then the test should fails, and if it passes, it fails.')
    return params

  def getCommand(self, options):
    ravenflag = ''
    if self.specs['test_interface_only'].lower() == 'true': ravenflag = 'interfaceCheck '
    if RavenUtils.inPython3():
      return "python3 " + self.driver + " " + ravenflag + self.specs["input"]
    else:
      return "python " + self.driver + " " + ravenflag + self.specs["input"]


  def __init__(self, name, params):
    Tester.__init__(self, name, params)
    self.csv_files = self.specs['csv'].split(" ") if len(self.specs['csv']) > 0 else []
    self.xml_files = self.specs['xml'].split(" ") if len(self.specs['xml']) > 0 else []
    self.ucsv_files = self.specs['UnorderedCsv'].split(" ") if len(self.specs['UnorderedCsv']) > 0 else []
    self.uxml_files = self.specs['UnorderedXml'].split(" ") if len(self.specs['UnorderedXml']) > 0 else []
    self.required_executable = self.specs['required_executable']
    self.required_libraries = self.specs['required_libraries'].split(' ')  if len(self.specs['required_libraries']) > 0 else []
    self.required_executable = self.required_executable.replace("%METHOD%",os.environ.get("METHOD","opt"))
    self.specs['scale_refine'] = False
    self.driver = os.path.join(RAVEN_DIR,'Driver.py')

  def checkRunnable(self, option):
    missing,too_old = _missing_modules, _too_old_modules
    if len(missing) > 0:
      return (False,'skipped (Missing python modules: '+" ".join(missing)+
              " PYTHONPATH="+os.environ.get("PYTHONPATH","")+')')
    if len(too_old) > 0:
      return (False,'skipped (Old version python modules: '+" ".join(too_old)+
              " PYTHONPATH="+os.environ.get("PYTHONPATH","")+')')
    for lib in self.required_libraries:
      found, message, version =  RavenUtils.moduleReport(lib,'')
      if not found:
        return (False,'skipped (Unable to import library: "'+lib+'")')
    if len(self.required_executable) > 0 and \
       not os.path.exists(self.required_executable):
      return (False,'skipped (Missing executable: "'+self.required_executable+'")')
    try:
      if len(self.required_executable) > 0 and \
         subprocess.call([self.required_executable],stdout=subprocess.PIPE) != 0:
        return (False,'skipped (Failing executable: "'+self.required_executable+'")')
    except:
      return (False,'skipped (Error when trying executable: "'+self.required_executable+'")')
    if len(self.specs['skip_if_env']) > 0:
      env_var = self.specs['skip_if_env']
      if env_var in os.environ:
        return (False,'skipped (found environmental variable "'+env_var+'")')
    return (True, '')

  def prepare(self):
    if self.specs['output'].strip() != '':
      self.check_files = [os.path.join(self.specs['test_dir'],filename)  for filename in self.specs['output'].split(" ")]
    else:
      self.check_files = []
    for filename in self.check_files+self.csv_files+self.xml_files+self.ucsv_files+self.uxml_files:# + [os.path.join(self.specs['test_dir'],filename)  for filename in self.csv_files]:
      if os.path.exists(filename):
        os.remove(filename)

  def processResults(self, moose_dir, retcode, options, output):
    expectedFail = self.specs['expected_fail'].lower().strip() == 'true'
    if not expectedFail:
      return self.rawProcessResults(moose_dir, retcode, options, output)
    else:
      reason, output = self.rawProcessResults(moose_dir, retcode, options, output)
      if reason == '':
        return ('Unexpected success', output)
      else:
        return ('', output)

  def rawProcessResults(self, moose_dir, retcode, options, output):
    missing = []
    for filename in self.check_files:
      if not os.path.exists(filename):
        missing.append(filename)

    if len(missing) > 0:
      return ('CWD '+os.getcwd()+' METHOD '+os.environ.get("METHOD","?")+' Expected files not created '+" ".join(missing),output)

    #csv
    if len(self.specs["rel_err"]) > 0:
      csv_diff = CSVDiffer(self.specs['test_dir'],self.csv_files,relative_error=float(self.specs["rel_err"]))
    else:
      csv_diff = CSVDiffer(self.specs['test_dir'],self.csv_files)
    message = csv_diff.diff()
    if csv_diff.getNumErrors() > 0:
      return (message,output)

    #unordered csv
    ucsv_diff = UnorderedCSVDiffer(self.specs['test_dir'],self.ucsv_files)
    ucsv_same,ucsv_messages = ucsv_diff.diff()
    if not ucsv_same:
      return ucsv_messages,output

    #xml
    xmlopts = {}
    if len(self.specs["rel_err"]) > 0: xmlopts['rel_err'] = float(self.specs["rel_err"])
    xmlopts['zero_threshold'] = float(self.specs["zero_threshold"])
    xmlopts['unordered'     ] = False
    xmlopts['remove_whitespace'] = self.specs['remove_whitespace'].lower().strip() == 'true'
    if len(self.specs['xmlopts'])>0: xmlopts['xmlopts'] = self.specs['xmlopts'].split(' ')
    xml_diff = XMLDiff(self.specs['test_dir'],self.xml_files,**xmlopts)
    (xml_same,xml_messages) = xml_diff.diff()
    if not xml_same:
      return (xml_messages,output)

    #unordered xml
    xmlopts['unordered'] = True
    uxml_diff = XMLDiff(self.specs['test_dir'],self.uxml_files,**xmlopts)
    (uxml_same,uxml_messages) = uxml_diff.diff()
    if not uxml_same:
      return (uxml_messages,output)

    return ('',output)
