data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- file.path(results_dir, "composition")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
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
starts <- read.csv(file.path(data_dir, "historical/persons.csv"), stringsAsFactors = FALSE)[, c(
  "blind_id",
  "start_date"
)]
h <- merge(h, starts, by = "blind_id")
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
hall <- h
h <- h[h$besh_only_classifier == 0, ]
d <- read.csv(file.path(data_dir, "contemporaneous/person_analysis.csv"), stringsAsFactors = FALSE, na.strings = c(
  "",
  "NA"
))
d <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(d[, c(
  "blind_id", "mechanism", "group",
  "year", "ic", "eligible_main"
)], read.csv(file.path(data_dir, "derived/contemporaneous_extended.csv"),
  stringsAsFactors = FALSE
), read.csv(file.path(data_dir, "instrument/analysis/person_variants.csv"),
  stringsAsFactors = FALSE
)[, c("blind_id", "org_id", "primary_main", "preK_PI", "unresolved")]))
d <- d[d$eligible_main == 1 & d$unresolved == 0, ]
d$A <- as.integer(d$group == "Required")
d$ic <- factor(d$ic)
d$yearf <- factor(d$year)
h <- merge(h, read.csv(file.path(data_dir, "derived/historical_prior_trials.csv")), by = "blind_id")
h$inst_log_k <- log(ave(rep(1, nrow(h)), h$org_id, FUN = sum))
covs <- c("preK_PI_nonK", "prior_nih_pi_award", "prior_research_grant", "inst_log_k")
bal <- list()
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  y <- d[d$mechanism == m, ]
  for (o in c("two_plus_trials", "primary_judgment_only", "primary_link_only")) {
    add("historical DID", m, o, "year FE + IC", boot(
      as.formula(paste(o, "~ intent*post + yearf + ic")),
      x, "intent:post"
    ))
  }
  add("main RD", m, "two_plus_trials", "unadjusted", boot(two_plus_trials ~ A, y, "A"))
  for (v in covs) {
    s <- boot(as.formula(paste(v, "~ intent*post + yearf + ic")), x, "intent:post")
    bal[[length(bal) + 1]] <- data.frame(mechanism = m, covariate = v, mean_pre_intent = round(mean(x[[v]][x$post ==
              0 & x$intent == 1]), 3), mean_post_intent = round(
        mean(x[[v]][x$post == 1 & x$intent == 1]),
        3
      ), mean_pre_nointent = round(mean(x[[v]][x$post == 0 & x$intent == 0]), 3),
      mean_post_nointent = round(mean(x[[v]][x$post ==
              1 & x$intent == 0]), 3), did = round(s["est"], 3), lo = round(s["lo"], 3), hi = round(
        s["hi"],
        3
      ), row.names = NULL)
  }
  for (o in c("primary", "ktrial_direct")) {
    add("historical DID", m, o, "adjusted for prior trial, prior NIH awards, institution size", boot(
      as.formula(paste(
        o,
        "~ intent*post + preK_PI_nonK + prior_nih_pi_award + prior_research_grant + inst_log_k + yearf + ic"
      )),
      x, "intent:post"
    ))
  }
}
ipw_fit <- function(x, o) {
  x <- droplevels(x)
  x$w <- 1
  for (it in 0:1) {
    s <- x$intent == it
    ps <- tryCatch(fitted(glm(post ~ preK_PI_nonK + prior_nih_pi_award + prior_research_grant + inst_log_k,
          family = binomial, data = x[s, ]
        )), error = function(e) stop("model fitting failed"))
    ps <- pmin(pmax(ps, 0.02), 0.98)
    x$w[s] <- ifelse(x$post[s] == 1, (1 - ps) / ps, 1)
  }
  f <- as.formula(paste(o, "~ intent*post + ic"))
  b <- tryCatch(coef(lm(f, data = x, weights = x$w))["intent:post"], error = function(e) stop("model fitting failed"))
  unname(b)
}
for (m in c("K23", "K08")) {
  for (o in c("primary", "ktrial_direct")) {
    x <- h[h$mechanism == m, ]
    est <- ipw_fit(x, o)
    cl <- split(seq_len(nrow(x)), x$org_id)
    reps <- replicate(n_boot, {
      ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
      ipw_fit(x[ix, ], o)
    })
    s <- c(est = est, lo = unname(quantile(reps, 0.025, na.rm = TRUE)), hi = unname(quantile(reps,
          0.975,
          na.rm = TRUE
        )), se = sd(reps, na.rm = TRUE), n = nrow(x), na = sum(is.na(reps)))
    add("historical DID", m, o, "reweighted to pre-policy covariates (IPW), IC FE", s)
  }
}
trim_did <- function(x, o, side) {
  s0 <- mean(x$intent[x$post == 0])
  s1 <- mean(x$intent[x$post == 1])
  q <- max(0, (s1 - s0) / s1)
  y1 <- sort(x[[o]][x$post == 1 & x$intent == 1], decreasing = (side == "lower"))
  k <- round(q * length(y1))
  y1 <- if (k > 0) {
    y1[-seq_len(k)]
  } else {
    y1
  }
  (mean(y1) - mean(x[[o]][x$post == 0 & x$intent == 1])) - (mean(x[[o]][x$post == 1 & x$intent == 0]) -
      mean(x[[o]][x$post == 0 & x$intent == 0]))
}
tb <- list()
for (m in c("K23")) {
  for (o in c("primary", "ktrial_direct")) {
    x <- h[h$mechanism == m, ]
    cl <- split(seq_len(nrow(x)), x$org_id)
    for (side in c("lower", "upper")) {
      est <- trim_did(x, o, side)
      reps <- replicate(n_boot, {
        ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
        trim_did(x[ix, ], o, side)
      })
      tb[[length(tb) + 1]] <- data.frame(mechanism = m, outcome = o, bound = side, trimmed_share = round(
        max(
          0,
          (mean(x$intent[x$post == 1]) - mean(x$intent[x$post == 0])) / mean(x$intent[x$post == 1])
        ),
        3
      ), estimate = round(100 * est, 1), lo = round(100 * quantile(reps, 0.025), 1), hi = round(100 *
          quantile(reps, 0.975), 1), row.names = NULL)
    }
  }
}
hh <- h
hh$k08 <- as.integer(hh$mechanism == "K08")
for (o in c("primary", "ktrial_direct", "informative_strict", "nih_new_trial_own_grant")) {
  add("pooled triple difference", "K08 minus K23", o, "intent x post x K08; year FE + IC", boot(as.formula(paste(
    o,
    "~ intent*post*k08 + yearf + ic"
  )), hh, "intent:post:k08"))
}
perm <- list()
x <- h[h$mechanism == "K08", ]
for (o in c("primary", "ktrial_direct", "informative_strict", "nih_new_trial_own_grant")) {
  cell <- function(p, it) {
    k <- sum(x[[o]][x$post == p & x$intent == it])
    n <- sum(x$post == p & x$intent == it)
    ci <- binom.test(k, n)$conf.int
    c(k = k, n = n, txt = sprintf("%d/%d (%.1f; %.1f to %.1f)", k, n, 100 * k / n, 100 * ci[1], 100 *
          ci[2]))
  }
  a0 <- cell(0, 1)
  a1 <- cell(1, 1)
  b0 <- cell(0, 0)
  b1 <- cell(1, 0)
  fx <- function(u, v) {
    fisher.test(matrix(as.integer(c(
      u["k"], as.integer(u["n"]) - as.integer(u["k"]),
      v["k"], as.integer(v["n"]) - as.integer(v["k"])
    )), 2))$p.value
  }
  perm[[length(perm) + 1]] <- data.frame(
    mechanism = "K08", outcome = o, pre_intent = a0["txt"], post_intent = a1["txt"],
    fisher_p_intent_change = signif(fx(a0, a1), 3), pre_nointent = b0["txt"], post_nointent = b1["txt"],
    fisher_p_nointent_change = signif(fx(b0, b1), 3), row.names = NULL
  )
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "estimates.csv"), row.names = FALSE)
write.csv(do.call(rbind, bal), file.path(out, "balance.csv"), row.names = FALSE)
write.csv(do.call(rbind, tb), file.path(out, "trimming_bounds.csv"), row.names = FALSE)
write.csv(do.call(rbind, perm), file.path(out, "k08_exact.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
