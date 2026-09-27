# Called from check_lucky_blocks.mcfunction, executing as the player whose
# family_lucky_heads stat just went up. Rolls the loot table at roughly
# where they're standing -- good enough; the exact broken block's position
# isn't available from a stat change alone.
loot spawn ~ ~ ~ loot family:lucky_block

# Breaking a player_head also drops that same head as an item. Without
# consuming it, placing the dropped head back down and breaking it again
# would roll again for free, forever, off one craft -- the whole point of
# making it craftable rather than spawnable is that each roll costs
# something. The crafted head is named ("Lucky Block", set in the recipe's
# custom_name component) so it can be told apart from an unrelated
# decorative head. It exists in exactly one of two places by the time this
# runs: still a dropped item on the ground, or already auto-picked-up into
# inventory. Checking once and branching -- rather than always clearing
# inventory and always trying to kill a dropped item -- matters because both
# commands can otherwise succeed on the same roll: if the drop hasn't been
# picked up yet *and* the player already carries an unrelated Lucky Block
# head from an earlier roll, the unconditional clear and the unconditional
# kill each remove a real head, consuming two for one break.
#
# Since 1.20.5 item NBT (`item{tag}`) was replaced by components
# (`item[component=...]`), including inside an item entity's own `Item`
# compound, where `tag` became `components`.
execute store success score #lucky_dropped family_temp if entity @e[type=item,distance=..2,limit=1,nbt={Item:{id:"minecraft:player_head",components:{"minecraft:custom_name":'{"text":"Lucky Block","color":"gold"}'}}}]
execute if score #lucky_dropped family_temp matches 1 run kill @e[type=item,distance=..2,limit=1,nbt={Item:{id:"minecraft:player_head",components:{"minecraft:custom_name":'{"text":"Lucky Block","color":"gold"}'}}}]
execute unless score #lucky_dropped family_temp matches 1 run clear @s minecraft:player_head[minecraft:custom_name='{"text":"Lucky Block","color":"gold"}'] 1
