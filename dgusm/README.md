# Fonts

## Hack NF
Horizontal Scale / Shift: -3 / -24
Vertical Scale / Shift: 0 / 0

## Share Tech Mono
Horizontal Scale / Shift: -2 / -32
Vertical Scale / Shift: 1 / 0

# Text Display Fixes

- Encoding: 8-bit
- "Set Character interval" for fixed-width
- Width needs to be "Text Length" * Y/2.  ie add 2px * "Text Length"
- X = Y/2
- "Horizontal Separation" = 0

## "Title" on each screen (VP 0x2)

- W = 160
- X = 40
- Y should already be 8

## "Message" on each screen (VP 0xa)

- Leave "Set Character interval" unchecked
- H = 40
- X = 210

## Boxes that are 46x18 (6 chars)

- W = 54
- Move left by 4

## Boxes that are 88x18 (12 chars)

- W = 108
- Move left by 6

## Boxes that are 262x20 (32 chars)

- W = 320
- X = 80 to center

## "Title" boxes 102x16 (16 chars)

- X = 131
- W = 128

## "Value" boxes 130x20 (16 chars)

- X = 131
- W = 160

## "Unit" boxes 48x20 (6 chars)

- X = 288
- W = 60

## "Button" boxes 130x20 (16 chars)

- X = 160
- W = 160


## Buttons that are 48x20 (6 chars)

- W = 60
- Move left by 6


# .plan

- Widen some of the backgrounds so text isn't on the edge
- Make "Message" area scroll or increase characters
- Add temperature graph
- See if "basic graphic display" would work for drawing custom screens
- Write a utility to dump .bin files to verify VPs, locations, and generate the controls.cfg file
- Icons on status page should do something (like being able to set temp / fan)
- Consolidate similar VPs from different pages at same addresses
- Left align menus?
- Make entire interface / text bigger?
- Use colors with more constrast
- Disabled up/down arrows should be invisible, not just darker.  The difference is minimal now.
- Make it easier to access pause / stop buttons?
- Add 1 decimal place to temperatures
- We can make beep longer than 2.55 seconds by reloading timer register manually.
