MAGUS control on 70 datasets: mean SPFN 11.884, SPFP 10.798, err 11.341 (%).

## best setting per strategy (lowest mean Δerr)

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| consensus_runs-modefilter-t0.5 | 70 | -0.686 | -0.705 | -0.696 | 60/5/5 | 5.3e-12 | 1.6e-11 | -0.745 | -1.000 | -0.674 | -0.032 | 5.41 | – | 0 |

## iterate

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| consensus_runs-modefilter-t0.5 | 70 | -0.686 | -0.705 | -0.696 | 60/5/5 | 5.3e-12 | 1.6e-11 | -0.745 | -1.000 | -0.674 | -0.032 | 5.41 | – | 0 |
| consensus_runs-modefilter-t0.75 | 70 | +0.690 | -1.770 | -0.540 | 54/10/6 | 1.4e-10 | 1.7e-10 | -0.653 | -0.767 | -0.474 | +0.011 | 5.40 | – | 0 |
| consensus_runs-modeweight | 70 | -0.491 | -0.717 | -0.604 | 57/7/6 | 8.4e-11 | 1.7e-10 | -0.613 | -0.914 | -0.595 | +0.017 | 5.42 | – | 0 |

