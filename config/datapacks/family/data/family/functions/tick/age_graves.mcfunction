# Called once per in-game day from check_sibling_rivalry.mcfunction's dawn
# detection -- reuses that day-transition logic rather than duplicating it
# for a second independent day counter.
#
# "@e" only matches entities in loaded chunks, so a grave's countdown only
# ticks down while its chunk happens to be loaded at dawn -- a grave far
# from wherever players currently are can sit frozen indefinitely instead
# of expiring on a real 24-day clock. Documented as 24 in-game days of
# loaded time (see docs/GRAVES.md) rather than forceloading every
# outstanding grave's chunk forever just to guarantee wall-clock accuracy
# for something this low-stakes.
scoreboard players remove @e[type=marker,tag=family_grave_marker] family_grave_age 1
execute as @e[type=marker,tag=family_grave_marker,scores={family_grave_age=..0}] at @s run function family:tick/expire_grave
