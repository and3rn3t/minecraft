# Called from make_grave.mcfunction (and recursively from itself),
# executing as the grave's marker entity, at the marker's position (which is
# the chest's position). Repeatedly pulls one nearby dropped item into the
# chest until either the chest is full (27 slots) or nothing is left within
# range.
#
# A chest's Items entries need an explicit Slot number, and 1.20.4 has no
# macros to inject a stored score into a command argument like
# "container.$(slot)" -- so which slot gets used is a fixed 27-way branch on
# family_grave_slot instead. Verbose, but each line is obviously correct on
# its own, which is worth more here than a cleverer, harder-to-verify
# alternative. "item replace block <pos> container.N from entity <selector>
# contents" is the command purpose-built for "take this entity's single held
# stack and put it in this container slot" -- contents is the slot name a
# single-stack holder like a dropped item entity uses.
execute unless score @s family_grave_slot matches ..26 run return 1
execute unless entity @e[type=item,distance=..3] run return 1

tag @e[type=item,distance=..3,sort=nearest,limit=1] add family_vacuum_target

execute if score @s family_grave_slot matches 0 run item replace block ~ ~ ~ container.0 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 1 run item replace block ~ ~ ~ container.1 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 2 run item replace block ~ ~ ~ container.2 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 3 run item replace block ~ ~ ~ container.3 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 4 run item replace block ~ ~ ~ container.4 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 5 run item replace block ~ ~ ~ container.5 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 6 run item replace block ~ ~ ~ container.6 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 7 run item replace block ~ ~ ~ container.7 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 8 run item replace block ~ ~ ~ container.8 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 9 run item replace block ~ ~ ~ container.9 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 10 run item replace block ~ ~ ~ container.10 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 11 run item replace block ~ ~ ~ container.11 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 12 run item replace block ~ ~ ~ container.12 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 13 run item replace block ~ ~ ~ container.13 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 14 run item replace block ~ ~ ~ container.14 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 15 run item replace block ~ ~ ~ container.15 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 16 run item replace block ~ ~ ~ container.16 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 17 run item replace block ~ ~ ~ container.17 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 18 run item replace block ~ ~ ~ container.18 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 19 run item replace block ~ ~ ~ container.19 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 20 run item replace block ~ ~ ~ container.20 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 21 run item replace block ~ ~ ~ container.21 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 22 run item replace block ~ ~ ~ container.22 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 23 run item replace block ~ ~ ~ container.23 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 24 run item replace block ~ ~ ~ container.24 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 25 run item replace block ~ ~ ~ container.25 from entity @e[tag=family_vacuum_target,limit=1] contents
execute if score @s family_grave_slot matches 26 run item replace block ~ ~ ~ container.26 from entity @e[tag=family_vacuum_target,limit=1] contents

kill @e[tag=family_vacuum_target,limit=1]
scoreboard players add @s family_grave_slot 1

function family:tick/vacuum_grave_step
