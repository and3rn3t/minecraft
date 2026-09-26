# Grants "Neighbors" to any player who has built within 50 blocks of Dad's
# house. x=100,y=64,z=100 is a placeholder — edit it to the real
# coordinates once (docs/ADVANCEMENTS.md explains how to find them in game)
# and /reload. The selector's distance= against literal coordinates is a true
# radial check; 1.20.4 has no macros to read a stored/settable location here.
execute as @a at @s if entity @s[x=100,y=64,z=100,distance=..50] run advancement grant @s only family:neighbors
