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
import os
import sys
frameworkDir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(frameworkDir,'utils'))
from utils import utils
utils.find_crow(frameworkDir)
distribution1D = utils.find_distribution1D()
stochasticEnv = distribution1D.DistributionContainer.instance()
import math
normal1 = distribution1D.BasicNormalDistribution(0.5, 0.05, 0.0,1.0)

def constrain(self):
  B, R = self.B, self.R
  f, d = 0.5, 0.5
  if B + R * f - d > 0:
    returnValue = 1
  else:
    returnValue = 0
  return returnValue
