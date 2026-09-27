# "Survived three nights with your brother." Counts an in-game day as
# survived-together if at least 2 players were online at dawn.
#
# 1.20.4 has no macros, so a function can't be told "the day just changed" —
# it has to notice. Store the current in-game time-of-day into a scoreboard
# score every tick, and treat the tick where it's back down near 0 as dawn.
# #counted_today guards against that multi-tick window near 0 being counted
# more than once in the same day.
# 26.1 replaced the old bare `time query daytime` keyword with a data-driven
# timeline registry; `time query day` is the current equivalent, returning
# ticks elapsed in the current repetition of the day/night cycle (still
# 0-23999), not a day count.
execute store result score #daytime family_temp run time query day

execute if score #daytime family_temp matches 0..5 unless score #counted_today family_temp matches 1 run function family:tick/on_dawn
execute if score #daytime family_temp matches 0..5 run scoreboard players set #counted_today family_temp 1
execute if score #daytime family_temp matches 6.. run scoreboard players set #counted_today family_temp 0

execute as @a if score #nights family_temp matches 3.. run advancement grant @s only family:sibling_rivalry
