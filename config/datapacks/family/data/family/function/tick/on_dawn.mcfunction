# Runs once per in-game day, from check_sibling_rivalry.mcfunction's dawn
# detection. Everything that only needs to happen once a day, not every
# tick, goes here rather than each duplicating the dawn-detection logic.
function family:tick/count_night
function family:tick/age_graves
