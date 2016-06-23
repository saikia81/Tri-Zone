# Tri-Zone
A python implementation of the game Tri-Zone by Williams

This has been build with an Raspberry pi, connected (via I2C) to multiple IO-expanders (MCP23017).
The IO-expanders are groupe by hardware types: [Solenoids, Lights, Switches]
(the switches are pressed by the ball, they're input)
We had an old Tri-Zone game, and fixed it up to be compatible.

Much is replaceable, but at the moment the code is a little untidy.

DEPENDENCIES
I2C_controller [see: https://github.com/saikia81/I2C_controller]


For any questions, do e-mail: saikia81@hotmail.com