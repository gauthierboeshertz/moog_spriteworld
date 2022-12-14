"""Task for receiving rewards upon contact."""

from . import abstract_task
import inspect
import numpy as np


class L2Reward(abstract_task.AbstractTask):
    """ContactReward task.
    
    In this task if any sprite in layers_0 contacts any sprite in layers_1, a
    reward is given. Otherwise the reward is zero. Optionally, the task resets
    upon such a contact.

    This can be used for any contact-based reward, such as prey-seeking and
    predator-avoidance.
    """

    def __init__(self,
                 layers_0,
                 layers_1,
                 condition=None,
                 reset_steps_after_contact=np.inf,
                 terminate_distance=0.05,
                 raw_reward_multiplier=5):
        """Constructor.

        Args:
            reward_fn: Scalar or function (sprite_0, sprite_1) --> scalar. If
                function, sprite_0 and sprite_1 are sprites in layers_0 and
                layers_1 respectively.
            layers_0: String or iterable of strings. Reward is given if a sprite
                in this layer(s) contacts a sprite in layers_1.
            layers_1: String or iterable of strings. Reward is given if a sprite
                in this layer(s) contacts a sprite in layers_0.
            condition: Optional condition function. If specified, must have one
                of the following signatures:
                    * sprite_0, sprite_1 --> bool
                    * sprite_0, sprite_1, meta_state --> bool
                The bool is whether to apply reward for those sprites
                contacting.
            reset_steps_after_contact: Int. How many steps after a contact to
                reset the environment. Defaults to infinity, i.e. never
                resetting.
        """
        
        if not isinstance(layers_0, (list, tuple)):
            layers_0 = [layers_0]
        self._layers_0 = layers_0

        if not isinstance(layers_1, (list, tuple)):
            layers_1 = [layers_1]
        self._layers_1 = layers_1

        if condition is None:
            self._condition = lambda s_agent, s_target, meta_state: True
        elif len(inspect.signature(condition).parameters.values()) == 2:
            self._condition = lambda s_a, s_t, meta_state: condition(s_a, s_t)
        else:
            self._condition = condition

        self._has_made_contact = False

        self._reset_steps_after_contact = reset_steps_after_contact
        self._terminate_distance = terminate_distance
        self._raw_reward_multiplier = raw_reward_multiplier

    def reset(self, state, meta_state):
        self._steps_until_reset = np.inf
        self._has_made_contact = False

    def has_finished(self):
        return self._has_made_contact

    def _single_sprite_reward(self, sprite,goal_position):
        goal_distance = np.sum( 
                              (sprite.position - goal_position)**2.)**0.5
        raw_reward = self._terminate_distance - goal_distance
        return self._raw_reward_multiplier * raw_reward

    def reward(self, state, meta_state, step_count):
        """Compute reward.
        
        If any sprite_0 in self._layers_0 overlaps any sprite_1 in
        self._layers_1 and if self._condition(sprite_0, sprite_1, meta_state) is
        True, then the reward is self._reward_fn(sprite_0, sprite_1).

        Args:
            state: OrderedDict of sprites. Environment state.
            meta_state: Environment state. Unconstrained type.
            step_count: Int. Environment step count.

        Returns:
            reward: Scalar reward.
            should_reset: Bool. Whether to reset task.
        """
        
        reward = 0
        sprites_0 = [s for k in self._layers_0 for s in state[k]]
        sprites_1 = [s for k in self._layers_1 for s in state[k]]

        reward = self._single_sprite_reward(sprites_0[0],sprites_1[0].position)

        if sprites_0[0].overlaps_sprite(sprites_1[0]):
            self._has_made_contact =  True
            if self._steps_until_reset == np.inf:
                self._steps_until_reset = (
                    self._reset_steps_after_contact)
        
        self._steps_until_reset -= 1
        
        should_reset = self._steps_until_reset < 0
        reward = reward * (1 - int(should_reset))
        #reward = reward if not self.has_made_contact else 0
        return reward, should_reset
