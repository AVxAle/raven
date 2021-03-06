# Copyright 2017 Battelle Energy Alliance, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import numpy as np

def initialize(self,runInfoDict,inputFiles):
  self.response = 3.0
  return

def run(self,Input):
  dim = 308
  # use a to represent the sensitivity
  senVec = np.loadtxt('sensitivity.txt')
  #senVec = np.random.rand(dim)
  varBase = 'x_'
  inputVar = []
  for i in range(dim):
    varname = varBase + str(i)
    inputVar.append(Input[varname])
  inputVar = np.asarray(inputVar)
  self.response = np.dot(senVec,inputVar)



