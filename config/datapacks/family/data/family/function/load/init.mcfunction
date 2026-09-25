# Runs once whenever this datapack loads (registered in
# data/minecraft/tags/function/load.json). "scoreboard objectives add" fails
# loudly if the objective already exists, which is fine here: each line of a
# function runs independently of the one before it, so a re-run on every
# /reload just reports a harmless error for objectives that already exist.

scoreboard objectives add family_blocks_mined dummy
scoreboard objectives add family_nights_together dummy
scoreboard objectives add family_temp dummy

# One scoreboard objective per block in the "Ten Thousand Blocks" curated
# list (docs/ADVANCEMENTS.md explains why it's a curated list rather than
# literally every block: vanilla has no single "mined, any block" stat).
scoreboard objectives add mined_stone minecraft.mined:minecraft.stone
scoreboard objectives add mined_deepslate minecraft.mined:minecraft.deepslate
scoreboard objectives add mined_dirt minecraft.mined:minecraft.dirt
scoreboard objectives add mined_cobblestone minecraft.mined:minecraft.cobblestone
scoreboard objectives add mined_sand minecraft.mined:minecraft.sand
scoreboard objectives add mined_gravel minecraft.mined:minecraft.gravel
scoreboard objectives add mined_oak_log minecraft.mined:minecraft.oak_log
scoreboard objectives add mined_coal_ore minecraft.mined:minecraft.coal_ore
scoreboard objectives add mined_iron_ore minecraft.mined:minecraft.iron_ore
scoreboard objectives add mined_copper_ore minecraft.mined:minecraft.copper_ore
scoreboard objectives add mined_diorite minecraft.mined:minecraft.diorite
scoreboard objectives add mined_andesite minecraft.mined:minecraft.andesite
