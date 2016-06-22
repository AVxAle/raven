"""
Module where the base class and the specialization of different type of optimizer (type of sampler) are
"""
#for future compatibility with Python 3--------------------------------------------------------------
from __future__ import division, print_function, unicode_literals, absolute_import
import warnings
warnings.simplefilter('default',DeprecationWarning)
#if not 'xrange' in dir(__builtins__): xrange = range
#End compatibility block for Python 3----------------------------------------------------------------

#External Modules------------------------------------------------------------------------------------
import sys
import os
import copy
import abc
import numpy as np
import json
from operator import mul,itemgetter
from collections import OrderedDict
from functools import reduce
from scipy import spatial
from scipy.interpolate import InterpolatedUnivariateSpline
import xml.etree.ElementTree as ET
import itertools
from math import ceil
from collections import OrderedDict
from sklearn import neighbors
from sklearn.utils.extmath import cartesian

if sys.version_info.major > 2: import pickle
else: import cPickle as pickle
#External Modules End--------------------------------------------------------------------------------

#Internal Modules------------------------------------------------------------------------------------
import utils
import mathUtils
from BaseClasses import BaseType
from Assembler import Assembler
import Distributions
import DataObjects
import TreeStructure as ETS
import SupervisedLearning
import pyDOE as doe
import Quadratures
import OrthoPolynomials
import IndexSets
import Models
import PostProcessors
import MessageHandler
import GridEntities
from AMSC_Object import AMSC_Object
distribution1D = utils.find_distribution1D()
#Internal Modules End--------------------------------------------------------------------------------

class Optimizer(utils.metaclass_insert(abc.ABCMeta,BaseType),Assembler):
  """
    This is the base class for optimizers
    Optimizer is a special type of samplers that own the optimization sampling strategy (Type) and they generate the
    input values to optimize a loss function. They do not have distributions inside!!!!

    --Instance--
    myInstance = Optimizer()
    myInstance.XMLread(xml.etree.ElementTree.Element)  This method generates all the information that will be permanent for the object during the simulation
 
    --usage--
    myInstance = Optimizer()
    myInstance.XMLread(xml.etree.ElementTree.Element)  This method generate all permanent information of the object from <Simulation>
    myInstance.whatDoINeed()                           -see Assembler class-
    myInstance.initialize()                            This method is called from the <Step> before the Step process start. In the base class it reset the counter to 0
    myInstance.amIreadyToProvideAnInput                Requested from <Step> used to verify that the sampler is available to generate a new input
    myInstance.generateInput(self,model,oldInput)      Requested from <Step> to generate a new input. Generate the new values and request to model to modify according the input and returning it back
 
    --Other inherited methods--
    myInstance.whoAreYou()                            -see BaseType class-
    myInstance.myCurrentSetting()                     -see BaseType class-
 
    --Adding a new Optimizer subclass--
    <MyClass> should inherit at least from Optimizer or from another derived class already presents
 
    DO NOT OVERRIDE any of the class method that are not starting with self.local*
 
    ADD your class to the dictionary __InterfaceDict in the Factory submodule
 
    The following method overriding is MANDATORY:
    self.localGenerateInput(model,oldInput)  : this is where the step happens, after this call the output is ready
    self._localGenerateAssembler(initDict)    
    self._localWhatDoINeed()
 
    the following methods could be overrode:
    self.localInputAndChecks(xmlNode)
    self.localGetInitParams()
    self.localGetCurrentSetting()
    self.localInitialize()
    self.localStillReady(ready)
    self.localFinalizeActualSampling(jobObject,model,myInput)
  """

  def __init__(self):
    """
      Default Constructor that will initialize member variables with reasonable
      defaults or empty lists/dictionaries where applicable.
      @ In, None
      @ Out, None
    """
    BaseType.__init__(self)
    Assembler.__init__(self)
    self.counter                        = {}
    self.counter['mdlEval']             = 0                         # Counter of the samples performed (better the input generated!!!). It is reset by calling the function self.initialize
    self.counter['varsUpdate']          = 0
    self.limit                          = {}
    self.limit['mdlEval']               = sys.maxsize               # maximum number of Samples (for example, Monte Carlo = Number of HistorySet to run, DET = Unlimited)
    self.limit['varsUpdate']            = sys.maxsize
    self.initSeed                       = None
    self.optVars                        = None                        # Decision variables for optimization
    self.optVarsBound                   = {}
    self.optVarsBound['upperBound']     = {}
    self.optVarsBound['lowerBound']     = {}
    self.optVarsHist                    = {}                        # History of Decision variables
    self.nVar                           = 0
    self.objVar                         = None
    self.optType                        = None
    self.convergenceTol                 = 1e-3
    self.solutionExport                 = None             #This is the data used to export the solution (it could also not be present)
    self.values                         = {}                        # for each variable the current value {'var name':value}
    self.inputInfo                      = {}                        # depending on the sampler several different type of keywarded information could be present only one is mandatory, see below
    self.inputInfo['SampledVars'     ]  = self.values               # this is the location where to get the values of the sampled variables
    self.FIXME                          = False                     # FIXME flag
    self.printTag                       = self.type                 # prefix for all prints (sampler type)

    self._endJobRunnable                = sys.maxsize               # max number of inputs creatable by the sampler right after a job ends (e.g., infinite for MC, 1 for Adaptive, etc)
    self.constraintFunction             = None

    self.mdlEvalHist                    = None
    self.objSearchingROM                = None
    
    self.addAssemblerObject('Restart' ,'-n',True)
    self.addAssemblerObject('TargetEvaluation','1')
    self.addAssemblerObject('Function','-1')
  
  def _localGenerateAssembler(self,initDict):
    """
      It is used for sending to the instanciated class, which is implementing the method, the objects that have been requested through "whatDoINeed" method
      It is an abstract method -> It must be implemented in the derived class!
      @ In, initDict, dict, dictionary ({'mainClassName(e.g., Databases):{specializedObjectName(e.g.,DatabaseForSystemCodeNamedWolf):ObjectInstance}'})
      @ Out, None
    """
    ## FIX ME -- this method is inherited from sampler and may not be needed by optimizer
    pass

  def _localWhatDoINeed(self):
    """
      This method is a local mirror of the general whatDoINeed method.
      It is implemented by the samplers that need to request special objects
      @ In, None
      @ Out, needDict, dict, list of objects needed
    """
    ## FIX ME -- this method is inherited from sampler and may not be neede by optimizer
    return {}

  def _readMoreXML(self,xmlNode):
    """
      Function to read the portion of the xml input that belongs to this specialized class
      and initialize some stuff based on the inputs got
      The text is supposed to contain the info where and which variable to change.
      In case of a code the syntax is specified by the code interface itself
      @ In, xmlNode, xml.etree.ElementTree.Element, Xml element node
      @ Out, None
    """
    Assembler._readMoreXML(self,xmlNode)    
    self._readMoreXMLbase(xmlNode)
    self.localInputAndChecks(xmlNode)

  def _readMoreXMLbase(self,xmlNode):
    """
      Function to read the portion of the xml input that belongs to the base sampler only
      and initialize some stuff based on the inputs got
      The text is supposed to contain the info where and which variable to change.
      In case of a code the syntax is specified by the code interface itself
      @ In, xmlNode, xml.etree.ElementTree.Element, Xml element node1
      @ Out, None
    """
    for child in xmlNode:
      if child.tag == "variable":
        if self.optVars == None:                    self.optVars = []
        varname = child.attrib['name']
        self.optVars.append(varname)
        for childChild in child:
          if childChild.tag == "upperBound":        self.optVarsBound['upperBound'][varname] = float(childChild.text)
          elif childChild.tag == "lowerBound":      self.optVarsBound['lowerBound'][varname] = float(childChild.text)
        
        if varname not in self.optVarsBound['upperBound'].keys():
          self.optVarsBound['upperBound'][varname] = sys.maxsize
        elif varname not in self.optVarsBound['lowerBound'].keys():
          self.optVarsBound['lowerBound'][varname] = -sys.maxsize        
      
      elif child.tag == "objectVar":
        self.objVar = child.text
        
      elif child.tag == "initialization":
        self.initSeed = Distributions.randomIntegers(0,2**31,self)
        for childChild in child:
          if childChild.tag == "limit":
            self.limit['mdlEval'] = int(childChild.text)
          elif childChild.tag == "type":
            self.optType = childChild.text
            if self.optType not in ['min', 'max']:
              self.raiseAnError(IOError, 'Unknown optimization type '+childChild.text+'. Available: mix or max')
          elif childChild.tag == "initialSeed":
            self.initSeed = int(childChild.text)
          else: self.raiseAnError(IOError,'Unknown tag '+childChild.tag+' .Available: limit, type, initialSeed!')
      
      elif child.tag == "convergence":
        self.convergenceTol = float(child.text)
        if 'limit' in child.attrib.keys():
          try   : self.limit['varsUpdate'] = int(child.attrib['limit'])
          except: self.raiseAnError(IOError,'Cannot convert limit value '+ child.attrib['limit']+ '!!!')       
      
      elif child.tag == "restartTolerance":
        self.restartTolerance = float(child.text)
      
    if self.optType == None:    self.optType = 'min'
    if self.initSeed == None:   self.initSeed = Distributions.randomIntegers(0,2**31,self)
    if self.objVar == None:     self.raiseAnError(IOError, 'Object variable is not specified for optimizer!')
    if self.optVars == None:    self.raiseAnError(IOError, 'Decision variable is not specified for optimizer!')
    
    
  def localInputAndChecks(self,xmlNode):
    """
      Local method. Place here the additional reading, remember to add initial parameters in the method localGetInitParams
      @ In, xmlNode, xml.etree.ElementTree.Element, Xml element node
      @ Out, None
    """
    pass # To be overwritten by subclass
      
  def endJobRunnable(self):
    """
      Returns the maximum number of inputs allowed to be created by the sampler
      right after a job ends (e.g., infinite for MC, 1 for Adaptive, etc)
      @ In, None
      @ Out, endJobRunnable, int, number of runnable jobs at the end of each sample
    """
    return self._endJobRunnable

  def getInitParams(self):
    """
      This function is called from the base class to print some of the information inside the class.
      Whatever is permanent in the class and not inherited from the parent class should be mentioned here
      The information is passed back in the dictionary. No information about values that change during the simulation are allowed
      @ In, None
      @ Out, paramDict, dict, dictionary containing the parameter names as keys
        and each parameter's initial value as the dictionary values
    """
    paramDict = {}
    for variable in self.optVars:
      paramDict[variable] = 'is sampled as a decision variable'
    paramDict['limit_mdlEval' ]        = self.limit['mdlEval']
    paramDict['initial seed' ] = self.initSeed
    paramDict.update(self.localGetInitParams())
    return paramDict

  def localGetInitParams(self):
    """
      Method used to export to the printer in the base class the additional PERMANENT your local class have
      @ In, None
      @ Out, paramDict, dict, dictionary containing the parameter names as keys
        and each parameter's initial value as the dictionary values
    """
    return {}

  def getCurrentSetting(self):
    """
      This function is called from the base class to print some of the information inside the class.
      Whatever is a temporary value in the class and not inherited from the parent class should be mentioned here
      The information is passed back in the dictionary
      @ In, None
      @ Out, paramDict, dict, dictionary containing the parameter names as keys
        and each parameter's initial value as the dictionary values
    """
    paramDict = {}
    paramDict['counter_mdlEval'       ] = self.counter['mdlEval']
    paramDict['counter_varsUpdate'    ] = self.counter['varsUpdate']
    paramDict['initial seed'  ] = self.initSeed
    for key in self.inputInfo:
      if key!='SampledVars':
        paramDict[key] = self.inputInfo[key]
      else:
        for var in self.inputInfo['SampledVars'].keys():
          paramDict['Variable: '+var+' has value'] = paramDict[key][var]
    paramDict.update(self.localGetCurrentSetting())
    return paramDict

  def localGetCurrentSetting(self):
    """
      Returns a dictionary with class specific information regarding the
      current status of the object.
      @ In, None
      @ Out, paramDict, dict, dictionary containing the parameter names as keys
        and each parameter's initial value as the dictionary values
    """
    return {}

  def checkConstraint(self, optVars):
    if self.constraintFunction == None:
      satisfaction = True
    else:
      satisfaction = True if self.constraintFunction.evaluate("constrain",optVars) == 1 else False
    satisfaction = self.localCheckConstraint(optVars, satisfaction)
    return satisfaction 
  
  def localCheckConstraint(self, optVars, satisfaction = True):
    return satisfaction # To be overwritten by subclass

  def initialize(self,externalSeeding=None,solutionExport=None):
    """
      This function should be called every time a clean sampler is needed. Called before takeAstep in <Step>
      @ In, externalSeeding, int, optional, external seed
      @ In, solutionExport, DataObject, optional, in goal oriented sampling (a.k.a. adaptive sampling this is where the space/point satisfying the constrains)
      @ Out, None
    """
    self.counter['mdlEval'] = 0
    self.counter['varsUpdate'] = 0
    self.nVar = len(self.optVars)
    
    self.mdlEvalHist = self.assemblerDict['TargetEvaluation'][0][3]    
    self.objSearchingROM = SupervisedLearning.returnInstance('SciKitLearn', self, **{'SKLtype':'neighbors|KNeighborsRegressor', 'Features':','.join(list(self.optVars)), 'Target':self.objVar, 'n_neighbors':1})
    self.solutionExport = solutionExport
    
    if solutionExport != None and type(solutionExport).__name__ != "PointSet":
      self.raiseAnError(IOError,'solutionExport type is not a PointSet. Got '+ type(solutionExport).__name__+ '!')    
    
    if 'Function' in self.assemblerDict.keys():
      self.constraintFunction = self.assemblerDict['Function'][0][3]
      if 'constrain' not in self.constrainFunction.availableMethods(): 
        self.raiseAnError(IOError,'the function provided to define the constraints must have an implemented method called "constrain"')
             
    if self.initSeed != None:           Distributions.randomSeed(self.initSeed)  
      
    if not externalSeeding:             Distributions.randomSeed(self.initSeed)       #use the sampler initialization seed
    elif externalSeeding=='continue':   pass        #in this case the random sequence needs to be preserved
    else:                               Distributions.randomSeed(externalSeeding)     #the external seeding is used
      
    #specializing the self.localInitialize() to account for adaptive sampling
    if solutionExport != None : self.localInitialize(solutionExport=solutionExport)
    else                      : self.localInitialize()

  def localInitialize(self,solutionExport=None):
    """
      use this function to add initialization features to the derived class
      it is call at the beginning of each step
      @ In, None
      @ Out, None
    """
    pass # To be overwritten by subclass

  def lossFunctionEval(self, optVars):
    tempDict = copy.copy(self.mdlEvalHist.getParametersValues('inputs', nodeid = 'RecontructEnding'))
    tempDict.update(self.mdlEvalHist.getParametersValues('outputs', nodeid = 'RecontructEnding'))
    for key in tempDict.keys():
      tempDict[key] = np.asarray(tempDict[key])
    self.objSearchingROM.train(tempDict)
    
    lossFunctionValue = self.searchingROM.evaluate(optVars)
    
    if self.optType == 'min':           return lossFunctionValue
    else:                               return lossFunctionValue*-1.0
    
  def amIreadyToProvideAnInput(self): #inLastOutput=None):
    """
      This is a method that should be call from any user of the sampler before requiring the generation of a new sample.
      This method act as a "traffic light" for generating a new input.
      Reason for not being ready could be for example: exceeding number of samples, waiting for other simulation for providing more information etc. etc.
      @ In, None
      @ Out, ready, bool, is this sampler ready to generate another sample?
    """
    ready = True if self.counter['mdlEval'] < self.limit['mdlEval'] and self.counter['varsUpdate'] < self.limit['varsUpdate'] else False
    convergence = self.checkConvergence()
    ready = self.localStillReady(ready, convergence)
    return ready

  def localStillReady(self,ready, convergence = False): #,lastOutput=None
    """
      Determines if sampler is prepared to provide another input.  If not, and
      if jobHandler is finished, this will end sampling.
      @ In,  ready, bool, a boolean representing whether the caller is prepared for another input.
      @ Out, ready, bool, a boolean representing whether the caller is prepared for another input.
    """
    return ready

  def checkConvergence(self):
    convergence = self.localCheckConvergence()
    return convergence

  @abc.abstractmethod
  def localCheckConvergence(self, convergence = False):
    return convergence

  def generateInput(self,model,oldInput):
    """
      This method has to be overwritten to provide the specialization for the specific sampler
      The model instance in might be needed since, especially for external codes,
      only the code interface possesses the dictionary for reading the variable definition syntax
      @ In, model, model instance, it is the instance of a RAVEN model
      @ In, oldInput, list, a list of the original needed inputs for the model (e.g. list of files, etc. etc)
      @ Out, generateInput, list, list containing the new inputs -in reality it is the model that return this the Sampler generate the value to be placed in the input the model
    """
    self.counter['mdlEval'] +=1                              #since we are creating the input for the next run we increase the counter and global counter
        
    self.inputInfo['prefix'] = str(self.counter['mdlEval'])
    model.getAdditionalInputEdits(self.inputInfo)
    self.localGenerateInput(model,oldInput)
    
    self.raiseADebug('Found new point to sample:',self.values)
    return 0,model.createNewInput(oldInput,self.type,**self.inputInfo)

  @abc.abstractmethod
  def localGenerateInput(self,model,oldInput):
    """
      This class need to be overwritten since it is here that the magic of the sampler happens.
      After this method call the self.inputInfo should be ready to be sent to the model
      @ In, model, model instance, it is the instance of a RAVEN model
      @ In, oldInput, list, a list of the original needed inputs for the model (e.g. list of files, etc. etc)
      @ Out, localGenerateInput, list, list containing the new inputs -in reality it is the model that return this the Sampler generate the value to be placed in the input the model
    """
    pass

#   def generateInputBatch(self,myInput,model,batchSize,projector=None): #,lastOutput=None
#     """
#       this function provide a mask to create several inputs at the same time
#       It call the generateInput function as many time as needed
#       @ In, myInput, list, list containing one input set
#       @ In, model, model instance, it is the instance of a RAVEN model
#       @ In, batchSize, int, the number of input sets required
#       @ In, projector, object, optional, used for adaptive sampling to provide the projection of the solution on the success metric
#       @ Out, newInputs, list of list, list of the list of input sets
#     """
# #     newInputs = []
# #     #inlastO = None
# #     #if lastOutput:
# #     #  if not lastOutput.isItEmpty(): inlastO = lastOutput
# #     #while self.amIreadyToProvideAnInput(inlastO) and (self.counter < batchSize):
# #     while self.amIreadyToProvideAnInput() and (self.counter < batchSize):
# #       if projector==None: newInputs.append(self.generateInput(model,myInput))
# #       else              : newInputs.append(self.generateInput(model,myInput,projector))
# #     return newInputs
#     pass

  def finalizeActualSampling(self,jobObject,model,myInput):
    """
      This function is used by samplers that need to collect information from a
      finished run.
      Provides a generic interface that all samplers will use, for specifically
      handling any sub-class, the localFinalizeActualSampling should be overridden
      instead, as finalizeActualSampling provides only generic functionality
      shared by all Samplers and will in turn call the localFinalizeActualSampling
      before returning.
      @ In, jobObject, instance, an instance of a JobHandler
      @ In, model, model instance, it is the instance of a RAVEN model
      @ In, myInput, list, the generating input
    """
    self.localFinalizeActualSampling(jobObject,model,myInput)

  def localFinalizeActualSampling(self,jobObject,model,myInput):
    """
      Overwrite only if you need something special at the end of each run....
      This function is used by samplers that need to collect information from the just ended run
      For example, for a Dynamic Event Tree case, this function can be used to retrieve
      the information from the just finished run of a branch in order to retrieve, for example,
      the distribution name that caused the trigger, etc.
      It is a essentially a place-holder for most of the sampler to remain compatible with the StepsCR structure
      @ In, jobObject, instance, an instance of a JobHandler
      @ In, model, model instance, it is the instance of a RAVEN model
      @ In, myInput, list, the generating input
    """
    pass

  def handleFailedRuns(self,failedRuns):
    """
      Collects the failed runs from the Step and allows samples to handle them individually if need be.
      @ In, failedRuns, list, list of JobHandler.ExternalRunner objects
      @ Out, None
    """
    self.raiseADebug('===============')
    self.raiseADebug('| RUN SUMMARY |')
    self.raiseADebug('===============')
    if len(failedRuns)>0:
      self.raiseAWarning('There were %i failed runs!  Run with verbosity = debug for more details.' %(len(failedRuns)))
      for run in failedRuns:
        metadata = run.returnMetadata()
        self.raiseADebug('  Run number %s FAILED:' %run.identifier,run.command)
        self.raiseADebug('      return code :',run.getReturnCode())
        if metadata is not None:
          self.raiseADebug('      sampled vars:')
          for v,k in metadata['SampledVars'].items():
            self.raiseADebug('         ',v,':',k)
    else:
      self.raiseADebug('All runs completed without returning errors.')
    self._localHandleFailedRuns(failedRuns)
    self.raiseADebug('===============')
    self.raiseADebug('  END SUMMARY  ')
    self.raiseADebug('===============')

  def _localHandleFailedRuns(self,failedRuns):
    """
      Specialized method for samplers to handle failed runs.  Defaults to failing runs.
      @ In, failedRuns, list, list of JobHandler.ExternalRunner objects
      @ Out, None
    """
    if len(failedRuns)>0:
      self.raiseAnError(IOError,'There were failed runs; aborting RAVEN.')



   
  




