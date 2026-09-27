# There is no single vanilla stat for "blocks mined, any type" — each block
# has its own mined:<block> criterion. This sums a curated set of common ones
# each tick (recomputed from the source stats, not incremented, so re-running
# it every tick can't double-count) and grants the advancement once the total
# passes 10000. See docs/ADVANCEMENTS.md for the block list and its limits.
#
# "scoreboard players operation" requires its source to resolve to exactly
# one entity even when the target is a selector like @a -- @a on both sides
# is not "pair each player with themselves", it's an error (or worse, with
# exactly one player online, an accident that looks like it works). Each
# line runs once per player instead, via "execute as @a run ... @s ... @s".
execute as @a run scoreboard players operation @s family_blocks_mined = @s mined_stone
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_deepslate
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_dirt
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_cobblestone
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_sand
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_gravel
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_oak_log
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_coal_ore
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_iron_ore
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_copper_ore
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_diorite
execute as @a run scoreboard players operation @s family_blocks_mined += @s mined_andesite

execute as @a[scores={family_blocks_mined=10000..}] run advancement grant @s only family:ten_thousand_blocks
