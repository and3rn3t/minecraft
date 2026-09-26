# Called at most once per in-game day, only from the dawn window detected in
# tick/check_sibling_rivalry. Counts the night as survived together only if
# at least 2 real players were online to see it end.
#
# "@a[limit=2]" alone would only test "does at least 1 player exist," not
# "are there 2" — a selector's limit bounds how many entities a command acts
# on, it isn't a count test. So the count is built explicitly instead.
scoreboard players set #online_count family_temp 0
execute as @a run scoreboard players add #online_count family_temp 1
execute if score #online_count family_temp matches 2.. run scoreboard players add #nights family_temp 1
