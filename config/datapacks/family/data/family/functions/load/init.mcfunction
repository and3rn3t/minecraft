# Runs once whenever this datapack loads (registered in
# data/minecraft/tags/functions/load.json). "scoreboard objectives add" fails
# loudly if the objective already exists, which is fine here: each line of a
# function runs independently of the one before it, so a re-run on every
# /reload just reports a harmless error for objectives that already exist.

scoreboard objectives add family_blocks_mined dummy
scoreboard objectives add family_nights_together dummy
scoreboard objectives add family_temp dummy

# Lucky Blocks (W7): a real vanilla stat catches every player_head break,
# compared tick-to-tick the same way Ten Thousand Blocks watches its stats.
scoreboard objectives add family_lucky_heads minecraft.mined:minecraft.player_head
scoreboard objectives add family_lucky_prev dummy

# Graves (W8): the real vanilla "deaths" stat, same tick-to-tick comparison.
scoreboard objectives add family_deaths minecraft.custom:minecraft.deaths
scoreboard objectives add family_deaths_prev dummy
# Countdown (in-game days) and next-empty-chest-slot, both carried on each
# grave's own marker entity, not a player objective -- a player can have
# several graves outstanding at once.
scoreboard objectives add family_grave_age dummy
scoreboard objectives add family_grave_slot dummy

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
