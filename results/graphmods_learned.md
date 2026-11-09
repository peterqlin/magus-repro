MAGUS control on 70 datasets: mean SPFN 11.884, SPFP 10.798, err 11.341 (%).

## best setting per strategy (lowest mean Δerr)

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| learned_weights-modecut-t0.5-featuresopal | 70 | +0.223 | -0.761 | -0.269 | 48/15/7 | 2.4e-08 | 1.4e-07 | -0.220 | -0.444 | -0.261 | -0.030 | 1.96 | 0.136 | 0 |

## learned

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| learned_weights-modecut-t0.3 | 70 | +0.017 | -0.162 | -0.073 | 23/42/5 | 0.0021 | 0.0084 | -0.059 | -0.136 | -0.077 | +0.037 | 0.89 | 0.153 | 0 |
| learned_weights-modecut-t0.5 | 70 | +0.399 | -0.573 | -0.087 | 25/34/11 | 0.0043 | 0.011 | -0.043 | -0.188 | -0.056 | -0.038 | 0.86 | 0.137 | 0 |
| learned_weights-modecut-t0.5-featuresopal | 70 | +0.223 | -0.761 | -0.269 | 48/15/7 | 2.4e-08 | 1.4e-07 | -0.220 | -0.444 | -0.261 | -0.030 | 1.96 | 0.136 | 0 |
| learned_weights-modeweight | 70 | +0.443 | -0.392 | +0.025 | 20/31/19 | 0.94 | 0.94 | +0.087 | -0.061 | +0.060 | +0.004 | 1.44 | 1.000 | 0 |
| learned_weights-modeweight-featuresopal | 70 | +0.312 | -0.508 | -0.098 | 33/24/13 | 0.0037 | 0.011 | -0.000 | -0.271 | -0.071 | -0.002 | 2.47 | 1.000 | 0 |
| learned_weights-modeweight2 | 70 | +1.224 | -0.852 | +0.186 | 14/22/34 | 0.0011 | 0.0054 | +0.252 | +0.057 | +0.306 | +0.072 | 1.31 | 0.999 | 0 |

