MAGUS control on 70 datasets: mean SPFN 11.884, SPFP 10.798, err 11.341 (%).

## best setting per strategy (lowest mean Δerr)

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iterate-modeboost-lam1 | 70 | -0.021 | +0.026 | +0.003 | 0/68/2 | 0.93 | 1 | +0.016 | -0.000 | -0.004 | -0.005 | 2.17 | – | 0 |

## iterate

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iterate-modeboost-lam1 | 70 | -0.021 | +0.026 | +0.003 | 0/68/2 | 0.93 | 1 | +0.016 | -0.000 | -0.004 | -0.005 | 2.17 | – | 0 |
| iterate-modefilter-factor0 | 70 | +0.009 | -0.001 | +0.004 | 0/69/1 | 0.78 | 1 | +0.012 | -0.001 | +0.001 | +0.001 | 1.50 | – | 0 |
| iterate-modefilter-factor0.25 | 70 | -0.024 | +0.033 | +0.005 | 0/69/1 | 0.97 | 1 | +0.022 | -0.001 | -0.002 | -0.007 | 2.11 | – | 0 |
| iterate-modefilter-factor0.25-rounds3 | 70 | -0.027 | +0.040 | +0.007 | 0/69/1 | 0.48 | 1 | +0.026 | +0.001 | -0.002 | -0.007 | 3.09 | – | 0 |

