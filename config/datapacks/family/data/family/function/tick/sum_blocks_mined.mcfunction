# There is no single vanilla stat for "blocks mined, any type" — each block
# has its own mined:<block> criterion. This sums a curated set of common ones
# each tick (recomputed from the source stats, not incremented, so re-running
# it every tick can't double-count) and grants the advancement once the total
# passes 10000. See docs/ADVANCEMENTS.md for the block list and its limits.
scoreboard players operation @a family_blocks_mined = @a mined_stone
scoreboard players operation @a family_blocks_mined += @a mined_deepslate
scoreboard players operation @a family_blocks_mined += @a mined_dirt
scoreboard players operation @a family_blocks_mined += @a mined_cobblestone
scoreboard players operation @a family_blocks_mined += @a mined_sand
scoreboard players operation @a family_blocks_mined += @a mined_gravel
scoreboard players operation @a family_blocks_mined += @a mined_oak_log
scoreboard players operation @a family_blocks_mined += @a mined_coal_ore
scoreboard players operation @a family_blocks_mined += @a mined_iron_ore
scoreboard players operation @a family_blocks_mined += @a mined_copper_ore
scoreboard players operation @a family_blocks_mined += @a mined_diorite
scoreboard players operation @a family_blocks_mined += @a mined_andesite

execute as @a[scores={family_blocks_mined=10000..}] run advancement grant @s only family:ten_thousand_blocks
