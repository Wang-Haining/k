wilson <- function(p, n) {
  z <- qnorm(.975)
  stopifnot(n > 0, p >= 0, p <= 1)
  center <- (p + z * z / (2 * n)) / (1 + z * z / n)
  radius <- z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
  c(max(0, center - radius), min(1, center + radius))
}
newcombe <- function(p1, p0, c1, c0) {
  c(max(-1, p1 - p0 - sqrt((p1 - c1[1])^2 + (c0[2] - p0)^2)), min(
    1,
    p1 - p0 + sqrt((c1[2] - p1)^2 + (p0 - c0[1])^2)
  ))
}
common <- function(x) {
  x <- x[complete.cases(x[, c("year", "ic")]), , drop = FALSE]
  if (!nrow(x)) {
    return(x)
  }
  x$stratum <- paste(x$year, x$ic, sep = "|")
  tt <- table(x$stratum, factor(x$A, levels = 0:1))
  x[x$stratum %in% rownames(tt)[rowSums(tt > 0) == 2], , drop = FALSE]
}
add_estimate <- function(x, base, mechanism, eligibility, endpoint, population, method, weights = NULL) {
  pid <- paste(mechanism, eligibility, endpoint, population, sep = "__")
  n <- sapply(1:0, function(a) sum(x$A == a))
  unknown <- sapply(1:0, function(a) sum(base$A == a & is.na(base[[endpoint]])))
  excluded <- sapply(1:0, function(a) sum(base$A == a & !is.na(base[[endpoint]])) - sum(x$A == a))
  row <- data.frame(mechanism, eligibility, endpoint, population,
    population_id = pid, method, n1 = n[1],
    n0 = n[2], unknown1 = unknown[1], unknown0 = unknown[2], known_excluded1 = excluded[1],
    known_excluded0 = excluded[2],
    events1 = sum(x[[endpoint]][x$A == 1]), events0 = sum(x[[endpoint]][x$A == 0]), p1 = NA_real_,
    p0 = NA_real_, RD = NA_real_, CI_low = NA_real_, CI_high = NA_real_, ESS1 = NA_real_, ESS0 = NA_real_,
    fisher_p = NA_real_, status = "insufficient_groups", interval_method = "", stringsAsFactors = FALSE
  )
  if (all(n > 0)) {
    if (is.null(weights)) {
      weights <- rep(1, nrow(x))
    }
    stopifnot(length(weights) == nrow(x), all(is.finite(weights)), all(weights > 0))
    if (method == "pooled_standardized") {
      tw <- prop.table(table(x$stratum))
      for (a in 0:1) {
        for (s in names(tw)) {
          weights[x$A == a & x$stratum == s] <- tw[[s]] / sum(x$A ==
              a & x$stratum == s)
        }
      }
    }
    p <- ess <- numeric(2)
    cis <- matrix(NA_real_, 2, 2)
    for (k in 1:2) {
      a <- 2 - k
      ix <- x$A == a
      w <- weights[ix] / sum(weights[ix])
      y <- x[[endpoint]][ix]
      p[k] <- sum(w * y) / sum(w)
      ess[k] <- 1 / sum(w * w)
      if (method == "pooled_standardized") {
        bounds <- vapply(names(tw), function(s) {
          ys <- x[[endpoint]][x$A == a & x$stratum == s]
          ps <- mean(ys)
          (wilson(ps, length(ys)) - ps) * tw[[s]]
        }, numeric(2))
        cis[k, ] <- c(max(0, p[k] - sqrt(sum(bounds[1, ]^2))), min(1, p[k] + sqrt(sum(bounds[2, ]^2))))
      } else {
        cis[k, ] <- wilson(p[k], ess[k])
      }
    }
    ci <- newcombe(p[1], p[2], cis[1, ], cis[2, ])
    row[, c("p1", "p0", "RD", "CI_low", "CI_high", "ESS1", "ESS0")] <- as.list(c(
      p, p[1] - p[2],
      ci, ess
    ))
    row$status <- "estimated"
    row$interval_method <- if (method == "raw") {
      "Wilson_Newcombe"
    } else if (method == "pooled_standardized") {
      "stratified_Wilson_MOVER_fixed_pooled_weights_approximation"
    } else {
      "Wilson_Newcombe_effective_N_fixed_weights_approximation"
    }
    if (method == "raw") {
      row$fisher_p <- fisher.test(matrix(c(row$events1, n[1] - row$events1, row$events0, n[2] -
              row$events0), nrow = 2, byrow = TRUE))$p.value
    }
  }
  estimates[[length(estimates) + 1]] <<- row # nolint: object_usage_linter.
  invisible(row)
}
