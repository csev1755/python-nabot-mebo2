=================
Movement
=================
Move the Robot
~~~~~~~~~~~~~~

.. code-block:: python

   import mebo2_nabot

   robot = mebo2_nabot.Robot()
   robot.forward(steps=2)
   robot.arm_up(steps=2)

Retrieve Joint Positions
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import mebo2_nabot

   robot = mebo2_nabot.Robot()
   print(robot.get_joint_positions())

.. autoclass:: mebo2_nabot.Robot
   :members:
   :exclude-members: Camera, Command, Position, Speaker, Microphone, getInstance

.. autoclass:: mebo2_nabot.Robot.Command
   :members:
   :undoc-members:
.. autoenum:: mebo2_nabot.Robot.Position
   :members:
   :undoc-members: