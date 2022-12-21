//! This module contains functions for pp qq plot.
//!
//! Functions are imported from `scipy` repo, see link below:
//! https://github.com/scipy/scipy/blob/main/scipy/special/cephes/polevl.h;
//! https://github.com/scipy/scipy/blob/main/scipy/special/cephes/ndtr.c;
//! https://github.com/scipy/scipy/blob/main/scipy/special/cephes/ndtri.c;

#![allow(clippy::excessive_precision)]

//
// statistic_functions.rs
// Author: noonchen - chennoon233@foxmail.com
// Created Date: December 21st 2022
// -----
// Last Modified: Wed Dec 21 2022
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

//
// functions from polevl.h
//

/// DESCRIPTION:
///
/// Evaluates polynomial of degree N:
///
/// y  =  C0  + C1 x + C2 x^2  +...+ CN x^N
///
/// Coefficients are stored in reverse order:
///
/// coef[0] = CN  , ..., coef[N] = C0  .
///
#[inline(always)]
fn polevl(x: f64, coef: &[f64], n: usize) -> f64 {
    let mut ans = 0.0;

    for (i, &c) in coef.iter().enumerate() {
        if i == 0 {
            ans = c;
        } else {
            ans = ans * x + c;
            if i == n {
                break;
            }
        }
    }
    ans
}

/// Assuming CN = 1.0, otherwise same as polevl
#[inline(always)]
fn p1evl(x: f64, coef: &[f64], n: usize) -> f64 {
    let mut ans = x + coef[0];

    for (i, &c) in coef.iter().enumerate() {
        if i == 0 {
            continue;
        } else {
            ans = ans * x + c;
            if i == n - 1 {
                break;
            }
        }
    }
    ans
}

//
// functions from ndtr.c
//

static P: [f64; 9] = [
    2.46196981473530512524E-10,
    5.64189564831068821977E-1,
    7.46321056442269912687E0,
    4.86371970985681366614E1,
    1.96520832956077098242E2,
    5.26445194995477358631E2,
    9.34528527171957607540E2,
    1.02755188689515710272E3,
    5.57535335369399327526E2,
];

static Q: [f64; 8] = [
    /* 1.00000000000000000000E0, */
    1.32281951154744992508E1,
    8.67072140885989742329E1,
    3.54937778887819891062E2,
    9.75708501743205489753E2,
    1.82390916687909736289E3,
    2.24633760818710981792E3,
    1.65666309194161350182E3,
    5.57535340817727675546E2,
];

static R: [f64; 6] = [
    5.64189583547755073984E-1,
    1.27536670759978104416E0,
    5.01905042251180477414E0,
    6.16021097993053585195E0,
    7.40974269950448939160E0,
    2.97886665372100240670E0,
];

static S: [f64; 6] = [
    /* 1.00000000000000000000E0, */
    2.26052863220117276590E0,
    9.39603524938001434673E0,
    1.20489539808096656605E1,
    1.70814450747565897222E1,
    9.60896809063285878198E0,
    3.36907645100081516050E0,
];

static T: [f64; 5] = [
    9.60497373987051638749E0,
    9.00260197203842689217E1,
    2.23200534594684319226E3,
    7.00332514112805075473E3,
    5.55923013010394962768E4,
];

static U: [f64; 5] = [
    /* 1.00000000000000000000E0, */
    3.35617141647503099647E1,
    5.21357949780152679795E2,
    4.59432382970980127987E3,
    2.26290000613890934246E4,
    4.92673942608635921086E4,
];

static MAXLOG: f64 = 7.09782712893383996732E2; /* log(DBL_MAX) */

static M_SQRT1_2: f64 = 0.70710678118654752440; /* 1/sqrt(2) */

#[inline(always)]
fn erf(x: f64) -> f64 {
    if f64::is_nan(x) {
        return f64::NAN;
    }

    if x < 0.0 {
        return -erf(-x);
    }

    if f64::abs(x) > 1.0 {
        return 1.0 - erfc(x);
    }

    let z = x * x;
    x * polevl(z, &T, 4) / p1evl(z, &U, 5)
}

#[inline(always)]
fn erfc(a: f64) -> f64 {
    if f64::is_nan(a) {
        return f64::NAN;
    }

    let x = f64::abs(a);
    if x < 1.0 {
        return 1.0 - erf(a);
    }

    let z = -a * a;
    if z >= -MAXLOG {
        let z = f64::exp(z);

        let (p, q) = if x < 8.0 {
            (polevl(x, &P, 8), p1evl(x, &Q, 8))
        } else {
            (polevl(x, &R, 5), p1evl(x, &S, 6))
        };
        let mut y = (z * p) / q;

        if a < 0.0 {
            y = 2.0 - y;
        }

        if y != 0.0 {
            return y;
        }
    }
    // underflow
    if a < 0.0 {
        2.0
    } else {
        0.0
    }
}

/// DESCRIPTION:
///
/// Returns the area under the Gaussian probability density
/// function, integrated from minus infinity to x:
#[inline(always)]
pub fn ndtr(a: f64) -> f64 {
    if f64::is_nan(a) {
        return f64::NAN;
    }

    let x = a * M_SQRT1_2;
    let z = f64::abs(x);

    if z < M_SQRT1_2 {
        0.5 + 0.5 * erf(x)
    } else if x > 0.0 {
        1.0 - 0.5 * erfc(z)
    } else {
        0.5 * erfc(z)
    }
}

//
// functions from ndtri.c
//

static S2PI: f64 = 2.50662827463100050242E0; /* sqrt(2pi) */

/* approximation for 0 <= |y - 0.5| <= 3/8 */
static P0: [f64; 5] = [
    -5.99633501014107895267E1,
    9.80010754185999661536E1,
    -5.66762857469070293439E1,
    1.39312609387279679503E1,
    -1.23916583867381258016E0,
];

static Q0: [f64; 8] = [
    /* 1.00000000000000000000E0, */
    1.95448858338141759834E0,
    4.67627912898881538453E0,
    8.63602421390890590575E1,
    -2.25462687854119370527E2,
    2.00260212380060660359E2,
    -8.20372256168333339912E1,
    1.59056225126211695515E1,
    -1.18331621121330003142E0,
];

/* Approximation for interval z = sqrt(-2 log y ) between 2 and 8
 * i.e., y between exp(-2) = .135 and exp(-32) = 1.27e-14.
 */
static P1: [f64; 9] = [
    4.05544892305962419923E0,
    3.15251094599893866154E1,
    5.71628192246421288162E1,
    4.40805073893200834700E1,
    1.46849561928858024014E1,
    2.18663306850790267539E0,
    -1.40256079171354495875E-1,
    -3.50424626827848203418E-2,
    -8.57456785154685413611E-4,
];

static Q1: [f64; 8] = [
    /*  1.00000000000000000000E0, */
    1.57799883256466749731E1,
    4.53907635128879210584E1,
    4.13172038254672030440E1,
    1.50425385692907503408E1,
    2.50464946208309415979E0,
    -1.42182922854787788574E-1,
    -3.80806407691578277194E-2,
    -9.33259480895457427372E-4,
];

/* Approximation for interval z = sqrt(-2 log y ) between 8 and 64
 * i.e., y between exp(-32) = 1.27e-14 and exp(-2048) = 3.67e-890.
 */

static P2: [f64; 9] = [
    3.23774891776946035970E0,
    6.91522889068984211695E0,
    3.93881025292474443415E0,
    1.33303460815807542389E0,
    2.01485389549179081538E-1,
    1.23716634817820021358E-2,
    3.01581553508235416007E-4,
    2.65806974686737550832E-6,
    6.23974539184983293730E-9,
];

static Q2: [f64; 8] = [
    /*  1.00000000000000000000E0, */
    6.02427039364742014255E0,
    3.67983563856160859403E0,
    1.37702099489081330271E0,
    2.16236993594496635890E-1,
    1.34204006088543189037E-2,
    3.28014464682127739104E-4,
    2.89247864745380683936E-6,
    6.79019408009981274425E-9,
];

static EXP_MINUS_2: f64 = 0.13533528323661269189;
/// DESCRIPTION:
///
/// Returns the argument, x, for which the area under the
/// Gaussian probability density function (integrated from
/// minus infinity to x) is equal to y.
///
/// For small arguments:
/// 0 < y < exp(-2), the program computes
/// z = sqrt( -2.0 * log(y) );  then the approximation is
/// x = z - log(z)/z  - (1/z) P(1/z) / Q(1/z).
/// There are two rational functions P/Q, one for 0 < y < exp(-32)
/// and the other for y up to exp(-2).
///
/// For larger arguments:
/// w = y - 0.5, and  x/sqrt(2pi) = w + w**3 R(w**2)/S(w**2)).
#[inline(always)]
pub fn ndtri(y0: f64) -> f64 {
    if y0 == 0.0 {
        return -f64::INFINITY;
    }
    if y0 == 1.0 {
        return f64::INFINITY;
    }
    if !(0.0..=1.0).contains(&y0) {
        return f64::NAN;
    }

    let mut code = 1;
    let mut y = y0;
    let y2;
    let mut x;

    if y > (1.0 - EXP_MINUS_2) {
        y = 1.0 - y;
        code = 0;
    }

    if y > EXP_MINUS_2 {
        y -= 0.5;
        y2 = y * y;
        x = y + y * (y2 * polevl(y2, &P0, 4) / p1evl(y2, &Q0, 8));
        x *= S2PI;
        return x;
    }

    x = f64::sqrt(-2.0 * f64::ln(y));
    let x0 = x - f64::ln(x) / x;

    let z = 1.0 / x;
    let x1 = if x < 8.0 {
        z * polevl(z, &P1, 8) / p1evl(z, &Q1, 8)
    } else {
        z * polevl(z, &P2, 8) / p1evl(z, &Q2, 8)
    };
    x = x0 - x1;
    if code != 0 {
        x = -x;
    }
    x
}
