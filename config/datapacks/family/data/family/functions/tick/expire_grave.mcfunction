# Called from age_graves.mcfunction, executing as the expiring grave's
# marker, at its position (the chest's position). "destroy" mode makes
# setblock behave like the block was actually mined -- for a chest, that
# includes spilling its contents as dropped items rather than just deleting
# them, which is the "after a day, items drop normally" part of the roadmap
# description.
setblock ~ ~ ~ air destroy
setblock ~ ~1 ~ air destroy
kill @s
