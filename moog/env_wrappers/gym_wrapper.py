# Copyright 2019 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Wrapper to make object-oriented games conform to the OpenAI Gym interface.

Note: This wrapper does not inherit from
abstract_wrapper.AbstractEnvironmentWrapper, because unlike other wrappers this
one (intentionally) changes the API of the environment.
"""

from dm_env import specs
from gym import spaces
import numpy as np
import gym  
from .gym_utils import *
from array2gif import write_gif
import copy

def _spec_to_space(spec):
    """Convert dm_env.specs to gym.Spaces."""
    if isinstance(spec, list):
        return spaces.Tuple([_spec_to_space(s) for s in spec])
    elif isinstance(spec, spaces.MultiDiscrete):
        return copy.deepcopy(spec)
    elif isinstance(spec, specs.BoundedArray):
        print("spec",spec)
        return spaces.Box(
            low=spec.minimum * np.ones(spec.shape),
            high=spec.maximum* np.ones(spec.shape),
            shape=spec.shape,
            dtype=spec.dtype)
    elif isinstance(spec, specs.BoundedArray):
        return spaces.Box(
            spec.minimum.item(),
            spec.maximum.item(),
            shape=spec.shape,
            dtype=spec.dtype)
    elif isinstance(spec, dict):
        print("not here")
        pass
    else:
        raise ValueError('Unknown type for specs: {}'.format(spec))


class GymWrapper(gym.Env):
    """Wraps a object-oriented game environment into a Gym interface.

    Observations will be a dictionary, with the same keys as the 'observers'
    dict provided when constructing a object-oriented game environment.
    Rendering is always performed, so calling render() is a no-op.
    """
    metadata = {'render.modes': ['rgb_array']}

    def __init__(self, env):
        self._env = env
        self._last_render = None
        self._action_space = None
        self._observation_space = None

        # Reset object-oriented to setup the observation_specs correctly
        self._env.reset()
        self.reward_range = (-float("inf"), float("inf"))
        self.spec = None

        self._rendered_frames = []

    @property
    def observation_space(self):
        if self._observation_space is None:
            components = {}
            for key, value in self._env.observation_spec().items():
                if "image" in key:
                    components[key] = spaces.Box(
                    0, 255, value.shape, dtype=np.uint8)
                else:
                    components[key] = spaces.Box(
                        0, 1, value.shape, dtype=value.dtype)

            if len(self._env.observation_spec().keys()) == 1 or (len(self._env.observation_spec().keys()) == 2 and "image" in components.keys()) :
                self._observation_space = components[list(self._env.observation_spec().keys())[0]]
            else:
                self._observation_space = spaces.Dict(components)

        return self._observation_space

    @property
    def action_space(self):
        if self._action_space is None:
            self._action_space = _spec_to_space(self._env.action_spec())
        return self._action_space

    def _process_obs(self, obs):
        """Convert and processes observations."""
        for k, v in obs.items():
            obs[k] = np.asarray(v)
            if obs[k].dtype == bool:
                # Convert boolean 'success' into an float32 to predict it.
                obs[k] = obs[k].astype(np.float32)
            if k == 'image':
                self._last_render = obs[k]

        if len(obs.keys()) == 1 or (len(obs.keys()) == 2 and "image" in obs.keys()) :
            return obs[list(obs.keys())[0]]
            
        return obs

    def seed(self,seed=None):
        self.np_random, seed = np_random(seed)
        return [seed]

    def step(self, action):
        """Main step function for the environment.

        Args:
            action: Array R^4

        Returns:
            obs: dict of observations. Follows from the 'renderers'
                configuration
                provided as parameters to object-oriented games.
            reward: scalar reward.
            done: True if terminal state.
            info: dict with extra information (e.g. discount factor).
        """
        time_step = self._env.step(action)

        obs = self._process_obs(time_step.observation)
        reward = time_step.reward or 0
        done = time_step.last()
        info = {'discount': time_step.discount}
        if "sprite_info" in time_step.observation.keys():
            info["sprite_info"] = time_step.observation["sprite_info"]
            
        if not "image" in time_step.observation.keys():
            obs = obs.astype(np.float)
        return obs, reward, done, info

    def reset(self):
        """Reset environment.

        Returns:
            obs: dict of observations. Follows from the 'renderers'
                configuration provided as parameters to object-oriented games.
        """
        time_step = self._env.reset()
        self._rendered_frames = []
        return self._process_obs(time_step.observation)

    def render(self, mode='rgb_array'):
        """Render function, noop for compatibility.

        Args:
            mode: unused, always returns an RGB array.

        Returns:
            Last RGB observation (cached from last observation with key
                'image').
        """
        del mode
        self._rendered_frames.append(self._last_render)
        return self._last_render

    def close(self):
        """Unused."""
    
    def save_episode_gif(self,gif_name):
        write_gif([np.transpose(f, axes=[2,0, 1]) for f in self._rendered_frames], gif_name, fps=30)