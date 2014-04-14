from util import *
from Tester import Tester
from CSVDiffer import CSVDiffer
import RavenUtils
import os, subprocess

class RavenPython(Tester):
  try:
    output_swig = subprocess.Popen(["swig","-version"],stdout=subprocess.PIPE).communicate()[0]
  except OSError:
    output_swig = "Failed"

  has_swig2 = "Version 2.0" in output_swig


  def getValidParams():
    params = Tester.getValidParams()
    params.addRequiredParam('input',"The python file to use for this test.")
    if os.environ.get("CHECK_PYTHON3","0") == "1":
      params.addParam('python_command','python3','The command to use to run python')
    else:
      params.addParam('python_command','python','The command to use to run python')
    params.addParam('requires_swig2', False, "Requires swig2 for test")

    return params
  getValidParams = staticmethod(getValidParams)

  def getCommand(self, options):
    return self.specs["python_command"]+" "+self.specs["input"]

  def __init__(self, name, params):
    Tester.__init__(self, name, params)
    self.specs['scale_refine'] = False

  def checkRunnable(self, option):
    if self.specs['requires_swig2'] and not RavenPython.has_swig2:
      return (False, 'skipped (No swig 2.0 found)')
    missing = RavenUtils.checkForMissingModules()
    if len(missing) > 0:
      return (False,'skipped (Missing python modules: '+" ".join(missing)+
              " PYTHONPATH="+os.environ.get("PYTHONPATH","")+')')
    return (True, '')

  def processResults(self, moose_dir,retcode, options, output):
    if retcode != 0:
      return (str(retcode),output)
    return ('',output)
