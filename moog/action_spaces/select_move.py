"""Discrete grid action space for controlling agent avatars."""

from . import abstract_action_space
from dm_env import specs
import numpy as np


class SelectMove(abstract_action_space.AbstractActionSpace):
  """Select-Move action space.

  This action space takes in a continuous vector of length 4 with each component
  in [0, 1]. This can be intuited as representing two consecutive clicks:
    [first_x, first_y, second_x, second_y].

  These two clicks are then processed to generate a position and a motion:
    * Position = [first_x, first_y]
    * Motion = scale * [second_x - 0.5, second_y - 0.5]

  If the Position, viewed as a point in the arena, lies inside of a sprite, that
  sprite will be moved by Motion, which is a scaled version of the second click
  relative to the center of the arena. If the Position does not lie inside of a
  sprite then no sprite will move. So to move a sprite you have to click on it
  and click on the direction you want it to move, like a touch screen.

  There is an optional control cost proportional to the norm of the motion.
  """

  def __init__(self, action_layers='agent',
                scale=1.0, motion_cost=0.0, noise_scale=None,instant_move=False):
    """Constructor.

    Args:
      scale: Multiplier by which the motion is scaled down. Should be in [0.0,
        1.0].
      motion_cost: Factor by which motion incurs cost.
      noise_scale: Optional stddev of the noise. If scalar, applied to all
        action space components. If vector, must have same shape as action.
    """
    self._scale = scale
    self._motion_cost = motion_cost
    self._noise_scale = noise_scale
    self._instant_move = instant_move
    self._action_spec = specs.BoundedArray(
        shape=(4,), dtype=np.float32, minimum=0.0, maximum=1.0)

    if not isinstance(action_layers, (list, tuple)):
        action_layers = (action_layers,)
    self._action_layers = action_layers


  def get_motion(self, action,sprite):
    #delta_pos = (action[2:] - 0.5) * self._scale
    delta_pos = action - sprite.position
    return delta_pos

  def apply_noise_to_action(self, action):
    if self._noise_scale:
      noise = np.random.normal(
          loc=0.0, scale=self._noise_scale, size=action.shape)
      return action + noise
    else:
      return action

  def get_sprite_from_position(self, position, sprites):
    for sprite in sprites[::-1]:
      if sprite.contains_point(position):
        return sprite
    return None

  def step(self, state, action):
    """Take an action and move the sprites.

    Args:
      action: Numpy array of shape (4,) in [0, 1]. First two components are the
        position selection, second two are the motion selection.
      sprites: Iterable of sprite.Sprite() instances. If a sprite is moved by
        the action, its position is updated.
      keep_in_frame: Bool. Whether to force sprites to stay in the frame by
        clipping their centers of mass to be in [0, 1].

    Returns:
      Scalar cost of taking this action.
    """
    #if action[0] != 0.5:
        #print(action)
    noised_action = self.apply_noise_to_action(action)
    position = noised_action[:2]

    sprites = []
    for action_layer in self._action_layers:
        for sprite in state[action_layer]:
            sprites.append(sprite)

    

    clicked_sprite = self.get_sprite_from_position(position, sprites)
    
    #if action[0] != 0.5:
    #    print(clicked_sprite)
    #    print("POS",sprites[0].position)

    if clicked_sprite is not None:
      motion = self.get_motion(noised_action[2:],clicked_sprite)
      #print("SPEED",clicked_sprite.velocity)
      if not self._instant_move:
          clicked_sprite.velocity += (motion / clicked_sprite.mass)*self._scale #self._action / sprite.mass
      else:
          clicked_sprite.velocity = (motion / clicked_sprite.mass)*self._scale
      #print("S AFET",clicked_sprite.velocity)
    

  def reset(self, state):
      """Reset action space at start of new episode."""

  def random_action(self):
      """Return randomly sampled action."""
      return np.random.uniform(0., 1., size=(4,))
  
  def action_spec(self):
      return self._action_spec
