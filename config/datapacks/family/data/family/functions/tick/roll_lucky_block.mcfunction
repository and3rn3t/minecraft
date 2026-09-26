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
# NBT) so it can be told apart from an unrelated decorative head; clear one
# from the inventory (the common case -- a block broken while standing on
# or next to it is usually already picked up by the time this runs, a tick
# later) and kill one matching dropped item nearby, in case it hasn't been
# picked up yet.
clear @s minecraft:player_head{display:{Name:'{"text":"Lucky Block","color":"gold"}'}} 1
kill @e[type=item,distance=..2,limit=1,nbt={Item:{id:"minecraft:player_head",tag:{display:{Name:'{"text":"Lucky Block","color":"gold"}'}}}}]
