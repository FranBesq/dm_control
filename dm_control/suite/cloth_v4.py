# Copyright 2017 The dm_control Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

"""Point-mass domain."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
from dm_env import specs
from dm_control import mujoco
from dm_control.rl import control
from dm_control.suite import base
from dm_control.suite import common
from dm_control.suite.utils import randomizers
from dm_control.utils import containers
from dm_control.utils import rewards
import numpy as np
import random
import mujoco_py


_DEFAULT_TIME_LIMIT = 20
SUITE = containers.TaggedTasks()
CORNER_INDEX_POSITION=[86,81,59,54]
CORNER_INDEX_ACTION=['B0_0','B0_8','B8_0','B8_8']
GEOM_INDEX=['G0_0','G0_8','G8_0','G8_8']

def get_model_and_assets():
  """Returns a tuple containing the model XML string and a dict of assets."""
  # return common.read_model('cloth_v0.xml'), common.ASSETS
  return common.read_model('cloth_v4.xml'),common.ASSETS





@SUITE.add('benchmarking', 'easy')
def easy(time_limit=_DEFAULT_TIME_LIMIT, random=None, environment_kwargs=None):
  """Returns the easy cloth task."""

  physics = Physics.from_xml_string(*get_model_and_assets())
  task = Cloth(randomize_gains=False, random=random)
  environment_kwargs = environment_kwargs or {}
  return control.Environment(
      physics, task, time_limit=time_limit, n_frame_skip=1, special_task=True, **environment_kwargs)

class Physics(mujoco.Physics):
  """physics for the point_mass domain."""
  def get_nearest_joint(self,position):
    joint_pos=self.named.data.geom_xpos[6:,:2]
    joint_to_pos_dist=np.linalg.norm((joint_pos-position),axis=-1)
    joint_id=np.argmin(joint_to_pos_dist)
    force_id=joint_id-5
    return force_id, joint_to_pos_dist[joint_id]




class Cloth(base.Task):
  """A point_mass `Task` to reach target with smooth reward."""

  def __init__(self, randomize_gains, random=None):
    """Initialize an instance of `PointMass`.

    Args:
      randomize_gains: A `bool`, whether to randomize the actuator gains.
      random: Optional, either a `numpy.random.RandomState` instance, an
        integer seed for creating a new `RandomState`, or None to select a seed
        automatically (default).
    """
    self._randomize_gains = randomize_gains
    # self.action_spec=specs.BoundedArray(
    # shape=(2,), dtype=np.float, minimum=0.0, maximum=1.0)
    super(Cloth, self).__init__(random=random)
    self._stored_action_position = None

  def action_spec(self, physics):
    """Returns a `BoundedArray` matching the `physics` actuators."""

    # action force(3) ~[-1,1]+ position to apply action(2)~[-.3,.3]

    return specs.BoundedArray(
        shape=(5,), dtype=np.float, minimum=[-1.0,-1.0,-1.0,-.3,-.3] , maximum=[1.0,1.0,1.0,.3,.3] )

  def initialize_episode(self,physics):


    physics.named.data.xfrc_applied['B3_4', :3] = np.array([0,0,-2])
    physics.named.data.xfrc_applied['B4_4', :3] = np.array([0,0,-2])


    physics.named.data.xfrc_applied[CORNER_INDEX_ACTION,:3]=np.random.uniform(-.5,.5,size=3)

    super(Cloth, self).initialize_episode(physics)

  def before_step(self, action, physics):
      """Sets the control signal for the actuators to values in `action`."""
  #     # Support legacy internal code.

      physics.named.data.xfrc_applied[1:, :3] = np.zeros((3,))
      action_force = action[:3]
      action_position = action[3:] * 0.3
      force_id, _ = physics.get_nearest_joint(action_position)
      physics.named.data.xfrc_applied[force_id,:3] = 5*action_force

      self._stored_action_position = action_position
      # print(action)
      # physics.named.data.xfrc_applied[CORNER_INDEX_ACTION,:3]=2*action
      # for i in range(4):
      #    if (action[i]>0).any():
      #      print("box")
      #
      #      physics.named.data.xpos['mark']=physics.named.data.xpos[CORNER_INDEX_ACTION[i]]
      #      print(physics.named.data.xpos['mark'])
      #      physics.named.model.mat_rgba['self']=np.ones(4)
           # print(physics.named.data.geom_xpos[GEOM_INDEX[i]])
           # print(physics.named.data.geom_xpos['mark'])

  #     physics.named.data.xfrc_applied['B0_0',:3]=action

      # physics.set_control(action)
      # physics.named.data.xfrc_applied['B0_0',:3]=action[:3]
      # physics.named.data.xfrc_applied['B8_0',:3 ]=action[3:6]
      # physics.named.data.xfrc_applied['B0_8',:3]=action[6:9]
      # physics.named.data.xfrc_applied['B8_8',:3 ]=action[9:]
      # physics.named.data.xfrc_applied['B0_0', 2] = 9.5
      # physics.named.data.xfrc_applied['B0_0',:2]=action[:2]
      # physics.named.data.xfrc_applied['B8_0',:2]=action[2:]
      # physics.named.data.xfrc_applied['B8_0', 2] = 9.5


  def get_observation(self, physics):
    """Returns an observation of the state."""
    obs = collections.OrderedDict()
    obs['position'] = physics.position()
    obs['velocity'] = physics.velocity()
    return obs

  def get_reward(self, physics):
    """Returns a reward to the agent."""

    pos_ll=physics.data.geom_xpos[86,:2]
    pos_lr=physics.data.geom_xpos[81,:2]
    pos_ul=physics.data.geom_xpos[59,:2]
    pos_ur=physics.data.geom_xpos[54,:2]

    if self._stored_action_position is None:
        nn_distance = 0
        print('NO self._stored_action_position')
    else:
        _, nn_distance =physics.get_nearest_joint(self._stored_action_position)
        print('YES self._stored_action_position', nn_distance)


    diag_dist1=np.linalg.norm(pos_ll-pos_ur)
    diag_dist2=np.linalg.norm(pos_lr-pos_ul)
    reward_dist=diag_dist1+diag_dist2 - nn_distance
    return reward_dist
