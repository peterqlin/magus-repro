MAGUS control on 70 datasets: mean SPFN 11.884, SPFP 10.798, err 11.341 (%).

## best setting per strategy (lowest mean Δerr)

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aligner_evidence-toolsopal+mafft-lam0.25-optimize1 | 70 | -1.089 | -0.286 | -0.688 | 63/6/1 | 1.5e-12 | 1.3e-11 | -0.659 | -0.997 | -0.697 | -0.108 | 4.01 | 1.000 | 0 |

## evidence

| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | Δerr 1000L3 | Δerr 1000M1 | Δerr 1000S1 | Δerr RNASim | merge× | edges kept | added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| aligner_evidence-toolsclustal-lam0.25 | 70 | -0.602 | -0.323 | -0.462 | 54/14/2 | 1.3e-11 | 5e-11 | -0.442 | -0.684 | -0.456 | -0.071 | 1.63 | 1.000 | 0 |
| aligner_evidence-toolsmafft-lam0.25 | 70 | -0.373 | -0.298 | -0.336 | 49/17/4 | 5.2e-10 | 1e-09 | -0.309 | -0.517 | -0.328 | -0.041 | 1.58 | 1.000 | 0 |
| aligner_evidence-toolsmafft-lam0.25-optimize1 | 70 | -0.795 | -0.085 | -0.440 | 57/11/2 | 6.5e-12 | 4.3e-11 | -0.423 | -0.653 | -0.395 | -0.141 | 2.70 | 1.000 | 0 |
| aligner_evidence-toolsopal+clustal-lam0.25 | 70 | -0.817 | -0.397 | -0.607 | 56/13/1 | 5.3e-12 | 4.3e-11 | -0.554 | -0.936 | -0.623 | -0.023 | 3.02 | 1.000 | 0 |
| aligner_evidence-toolsopal+mafft-lam0.25 | 70 | -0.780 | -0.409 | -0.595 | 56/12/2 | 6.3e-12 | 4.3e-11 | -0.532 | -0.925 | -0.622 | -0.007 | 2.92 | 1.000 | 0 |
| aligner_evidence-toolsopal+mafft-lam0.25-optimize1 | 70 | -1.089 | -0.286 | -0.688 | 63/6/1 | 1.5e-12 | 1.3e-11 | -0.659 | -0.997 | -0.697 | -0.108 | 4.01 | 1.000 | 0 |
| aligner_evidence-toolsopal+mafft+clustal-lam0.25 | 70 | -0.759 | -0.381 | -0.570 | 56/12/2 | 6e-12 | 4.3e-11 | -0.519 | -0.875 | -0.578 | -0.043 | 3.59 | 1.000 | 0 |
| aligner_evidence-toolsopal+mafft+clustal-lam0.5 | 70 | -0.801 | -0.427 | -0.614 | 54/13/3 | 3.5e-11 | 1.1e-10 | -0.596 | -0.976 | -0.569 | -0.017 | 3.57 | 1.000 | 0 |
| aligner_evidence-toolsopal+mafft+clustal-modevote-lam0.5 | 70 | -0.153 | -0.528 | -0.340 | 46/18/6 | 8.9e-09 | 8.9e-09 | -0.245 | -0.604 | -0.327 | -0.031 | 3.59 | 1.000 | 0 |

