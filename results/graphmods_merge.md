MAGUS control on 70 datasets: mean SPFN 11.884, SPFP 10.798, err 11.341 (%).

## best setting per strategy (lowest mean Δerr)

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| strict_k_optimize-K5 | 70 | -0.171 | -0.053 | -0.112 | 37/26/7 | 6.3e-06 | 1.3e-05 | -0.064 | -0.170 | -0.112 | -0.092 | 0.42 | 0.169 | 0 |
| trace-traceminclusters-optimizetrue | 70 | -0.396 | +0.219 | -0.088 | 28/41/1 | 8.9e-09 | 4.5e-08 | -0.082 | -0.076 | -0.104 | -0.095 | 1.96 | 1.000 | 0 |

## merge

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| strict_k_optimize-K3 | 70 | -0.396 | +0.184 | -0.106 | 32/38/0 | 5.5e-09 | 3.3e-08 | -0.103 | -0.109 | -0.110 | -0.097 | 0.62 | 0.284 | 0 |
| strict_k_optimize-K4 | 70 | -0.345 | +0.129 | -0.108 | 34/34/2 | 2.6e-08 | 1e-07 | -0.094 | -0.126 | -0.103 | -0.110 | 0.51 | 0.208 | 0 |
| strict_k_optimize-K5 | 70 | -0.171 | -0.053 | -0.112 | 37/26/7 | 6.3e-06 | 1.3e-05 | -0.064 | -0.170 | -0.112 | -0.092 | 0.42 | 0.169 | 0 |
| trace-traceminclusters-optimizetrue | 70 | -0.396 | +0.219 | -0.088 | 28/41/1 | 8.9e-09 | 4.5e-08 | -0.082 | -0.076 | -0.104 | -0.095 | 1.96 | 1.000 | 0 |
| trace-tracemwtgreedy-optimizefalse | 70 | +0.177 | -0.109 | +0.034 | 3/54/13 | 0.03 | 0.03 | +0.099 | +0.025 | +0.015 | -0.040 | 1.20 | 1.000 | 0 |
| trace-tracemwtgreedy-optimizetrue | 70 | -0.388 | +0.217 | -0.085 | 26/41/3 | 2.3e-07 | 7e-07 | -0.052 | -0.100 | -0.101 | -0.092 | 2.17 | 1.000 | 0 |

