# Return only the two calendar-start restrictions used by the models.
local({
  x <- read.csv(file.path(Sys.getenv("DATA_DIR"), "historical/persons.csv"), stringsAsFactors = FALSE)
  if (Sys.getenv("PUBLIC") != "1") {
    x$start_ge_2018 <- as.integer(x$start_date >= "2018-01-01")
    x$start_ge_2017_09 <- as.integer(x$start_date >= "2017-09-01")
  }
  x[, c("blind_id", "start_ge_2018", "start_ge_2017_09")]
})
