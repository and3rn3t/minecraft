# Called from make_grave.mcfunction (and recursively from itself),
# executing as the grave's marker entity, at the marker's position (which is
# the chest's position). Repeatedly pulls one nearby dropped item into the
# chest until either the chest is full (27 slots) or nothing is left within
# range.
#
# Verified against a real running 1.20.4 server, not just reasoned through --
# and it took three attempts to get right, all confirmed live:
#
# 1. "item replace block <pos> container.N from entity <selector> contents"
#    (the command the Minecraft Wiki's /item page describes for "copy this
#    entity's single held stack into a container slot") fails outright on
#    1.20.4 with "Unknown slot 'contents'". That slot name is apparently a
#    later addition; the wiki content available while building this did not
#    make the version boundary clear.
# 2. "data modify block <pos> Items append from entity <selector> Item"
#    (skipping the Slot field entirely) *looks* like it works for one item,
#    but doesn't actually append: a chest's Items list is re-derived from
#    its live, slot-indexed inventory on every access, and an entry with no
#    Slot field defaults to slot 0 -- so appending a second item silently
#    overwrites the first rather than adding a second entry. This is true
#    even if a separate follow-up command sets Items[-1].Slot afterwards:
#    by the time that runs, the previous item is already gone, because the
#    same revalidation drops any entry without a complete, valid id+Count+
#    Slot the moment anything else touches the container.
# 3. The fix: build the *complete* entry -- id, Count and Slot all present
#    at once -- somewhere the container's revalidation can't touch it
#    (NBT storage, which has no such semantics), then commit it to the
#    chest in one atomic append. Storage isn't declared anywhere in
#    load/init.mcfunction; data modify creates it on first write.
#
# A chest has 27 slots, and 1.20.4 has no macros to inject a stored score
# into a command argument, so which slot number gets written is a fixed
# 27-way branch on family_grave_slot rather than a computed index --
# verbose, but every line is obviously correct on its own.
execute unless score @s family_grave_slot matches ..26 run return 1
execute unless entity @e[type=item,distance=..3] run return 1

tag @e[type=item,distance=..3,sort=nearest,limit=1] add family_vacuum_target
data modify storage family:temp Entry set from entity @e[tag=family_vacuum_target,limit=1] Item

execute if score @s family_grave_slot matches 0 run data modify storage family:temp Entry.Slot set value 0b
execute if score @s family_grave_slot matches 1 run data modify storage family:temp Entry.Slot set value 1b
execute if score @s family_grave_slot matches 2 run data modify storage family:temp Entry.Slot set value 2b
execute if score @s family_grave_slot matches 3 run data modify storage family:temp Entry.Slot set value 3b
execute if score @s family_grave_slot matches 4 run data modify storage family:temp Entry.Slot set value 4b
execute if score @s family_grave_slot matches 5 run data modify storage family:temp Entry.Slot set value 5b
execute if score @s family_grave_slot matches 6 run data modify storage family:temp Entry.Slot set value 6b
execute if score @s family_grave_slot matches 7 run data modify storage family:temp Entry.Slot set value 7b
execute if score @s family_grave_slot matches 8 run data modify storage family:temp Entry.Slot set value 8b
execute if score @s family_grave_slot matches 9 run data modify storage family:temp Entry.Slot set value 9b
execute if score @s family_grave_slot matches 10 run data modify storage family:temp Entry.Slot set value 10b
execute if score @s family_grave_slot matches 11 run data modify storage family:temp Entry.Slot set value 11b
execute if score @s family_grave_slot matches 12 run data modify storage family:temp Entry.Slot set value 12b
execute if score @s family_grave_slot matches 13 run data modify storage family:temp Entry.Slot set value 13b
execute if score @s family_grave_slot matches 14 run data modify storage family:temp Entry.Slot set value 14b
execute if score @s family_grave_slot matches 15 run data modify storage family:temp Entry.Slot set value 15b
execute if score @s family_grave_slot matches 16 run data modify storage family:temp Entry.Slot set value 16b
execute if score @s family_grave_slot matches 17 run data modify storage family:temp Entry.Slot set value 17b
execute if score @s family_grave_slot matches 18 run data modify storage family:temp Entry.Slot set value 18b
execute if score @s family_grave_slot matches 19 run data modify storage family:temp Entry.Slot set value 19b
execute if score @s family_grave_slot matches 20 run data modify storage family:temp Entry.Slot set value 20b
execute if score @s family_grave_slot matches 21 run data modify storage family:temp Entry.Slot set value 21b
execute if score @s family_grave_slot matches 22 run data modify storage family:temp Entry.Slot set value 22b
execute if score @s family_grave_slot matches 23 run data modify storage family:temp Entry.Slot set value 23b
execute if score @s family_grave_slot matches 24 run data modify storage family:temp Entry.Slot set value 24b
execute if score @s family_grave_slot matches 25 run data modify storage family:temp Entry.Slot set value 25b
execute if score @s family_grave_slot matches 26 run data modify storage family:temp Entry.Slot set value 26b

data modify block ~ ~ ~ Items append from storage family:temp Entry

kill @e[tag=family_vacuum_target,limit=1]
scoreboard players add @s family_grave_slot 1

function family:tick/vacuum_grave_step
