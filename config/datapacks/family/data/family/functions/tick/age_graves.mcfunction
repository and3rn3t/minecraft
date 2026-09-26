# Called once per in-game day from check_sibling_rivalry.mcfunction's dawn
# detection -- reuses that day-transition logic rather than duplicating it
# for a second independent day counter.
scoreboard players remove @e[type=marker,tag=family_grave_marker] family_grave_age 1
execute as @e[type=marker,tag=family_grave_marker,scores={family_grave_age=..0}] at @s run function family:tick/expire_grave
