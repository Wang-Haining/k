data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
n_boot <- 1000
fit <- function(formula, x, term) {
  x <- droplevels(x)
  drop <- Filter(function(v) is.factor(x[[v]]) && nlevels(x[[v]]) < 2, all.vars(formula))
  if (length(drop)) {
    formula <- update(formula, as.formula(paste(". ~ . -", paste(drop, collapse = " - "))))
  }
  b <- tryCatch(coef(lm(formula, data = x))[term], error = function(e) stop("model fitting failed"))
  if (is.na(b)) {
    NA_real_
  } else {
    unname(b)
  }
}
boot <- function(formula, x, term) {
  est <- fit(formula, x, term)
  cl <- split(seq_len(nrow(x)), x$org_id)
  reps <- replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    fit(formula, x[ix, ], term)
  })
  c(est = est, lo = unname(quantile(reps, 0.025, na.rm = TRUE)), hi = unname(quantile(reps, 0.975,
        na.rm = TRUE
      )), se = sd(reps, na.rm = TRUE), n = nrow(x), na = sum(is.na(reps)))
}
res <- list()
add <- function(analysis, m, outcome, spec, s, scale = 100) {
  res[[length(res) + 1]] <<- data.frame(
    analysis = analysis, mechanism = m, outcome = outcome, spec = spec,
    estimate = round(scale * s["est"], 1), lo = round(scale * s["lo"], 1), hi = round(
      scale * s["hi"],
      1
    ), se = round(scale * s["se"], 2), mde80 = round(2.8 * scale * s["se"], 1), n = s["n"],
    na_reps = s["na"], row.names = NULL
  )
}
h <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(read.csv(file.path(data_dir,
        "historical/person_analysis.csv"),
      stringsAsFactors = FALSE
    ), read.csv(file.path(data_dir, "derived/historical_extended.csv"), stringsAsFactors = FALSE)))
starts <- source("analysis/start_flags.R")$value
h <- merge(h, starts, by = "blind_id")
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
hall <- h
h <- h[h$besh_only_classifier == 0, ]
h <- merge(h, read.csv(file.path(data_dir, "derived/historical_prior_trials.csv")), by = "blind_id")
pre <- hall[hall$post == 0, ]
pre <- merge(pre, read.csv(file.path(data_dir, "derived/historical_prior_trials.csv")), by = "blind_id")
cap <- aggregate(preK_PI_nonK ~ org_id, data = pre, FUN = mean)
names(cap)[2] <- "cap"
h <- merge(h, cap, by = "org_id", all.x = TRUE)
h$cap[is.na(h$cap)] <- 0
h$high <- as.integer(h$cap > median(h$cap[h$mechanism == "K23"]))
x <- h[h$mechanism == "K23", ]
for (o in c("primary", "ktrial_direct")) {
  add("capacity triple difference", "K23", o, "intent x post x high-capacity institution", boot(as.formula(paste(
    o,
    "~ intent*post*high + yearf + ic"
  )), x, "intent:post:high"))
  for (g in 0:1) {
    add("DID by institutional capacity", "K23", o, ifelse(g == 1, "high-capacity institutions",
        "other institutions"
      ), boot(as.formula(paste(o, "~ intent*post + yearf + ic")), x[x$high == g, ], "intent:post"))
  }
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "historical/prior_capacity.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
