# Lucky Blocks (W7): breaking a crafted player_head rolls a loot table.
#
# There is no vanilla advancement trigger for "a specific block type was
# mined" (confirmed against the current advancement trigger list -- despite
# how it reads, "minecraft:mine_block" does not exist). Same tick-to-tick
# stat comparison as Ten Thousand Blocks instead: family_lucky_heads is bound
# to the real minecraft.mined:minecraft.player_head stat.
#
# This fires on *any* player_head break, not just ones crafted as a lucky
# block -- a decorative head statue would trigger it too. Acceptable on a
# two-kid home server; not worth position-tracking which specific head this
# was.

# A score compared to itself only fails when it doesn't exist yet, so this
# initializes family_lucky_prev to the current count the first time a player
# is seen -- without it, an unset "prev" reads as "different from current"
# and every player would roll one spurious lucky-block drop on their first
# tick after joining or after /reload.
execute as @a unless score @s family_lucky_prev = @s family_lucky_prev run scoreboard players operation @s family_lucky_prev = @s family_lucky_heads

execute as @a at @s unless score @s family_lucky_heads = @s family_lucky_prev run function family:tick/roll_lucky_block
execute as @a run scoreboard players operation @s family_lucky_prev = @s family_lucky_heads
