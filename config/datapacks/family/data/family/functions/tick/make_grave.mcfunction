# Called from check_deaths.mcfunction, executing as the player who just
# died, at their death position. Unlocked, labeled chest -- vanilla has no
# per-player container lock (Lock NBT restricts by item name, not player
# identity), so this can't actually be limited to the dead player. It relies
# on the honor system between two siblings rather than any enforcement. See
# docs/ADVANCEMENTS.md.
#
# "family_grave_new" is a throwaway tag distinguishing the marker just
# summoned from any other grave's marker that might be nearby (two players
# dying in the same spot, or a previous grave not yet expired).
# "family_grave_marker" is permanent -- it's how age_graves.mcfunction finds
# every outstanding grave later, and it IS this grave's position: nothing
# else records where a grave is.
#
# Everything from here on runs "as" the marker rather than the dead player,
# so @s consistently means the marker (its own family_grave_slot score) for
# the rest of this chain, matching vacuum_grave_step.mcfunction's own
# assumption about what @s means.
summon minecraft:marker ~ ~ ~ {Tags:["family_grave_marker","family_grave_new"]}

execute as @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] at @s run setblock ~ ~ ~ minecraft:chest
execute as @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] at @s run setblock ~ ~1 ~ minecraft:oak_sign
execute as @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] at @s run data modify block ~ ~1 ~ front_text.messages[0] set value "R.I.P."
execute as @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] at @s run data modify block ~ ~1 ~ front_text.messages[1] set value "A grave, unlocked."
execute as @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] at @s run data modify block ~ ~1 ~ front_text.messages[2] set value "Please don't loot it."

scoreboard players set @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] family_grave_slot 0
execute as @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] at @s run function family:tick/vacuum_grave_step

scoreboard players set @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] family_grave_age 24
tag @e[type=marker,tag=family_grave_new,limit=1,sort=nearest] remove family_grave_new
