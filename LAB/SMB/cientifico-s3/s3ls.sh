#!/usr/bin/env bash
set -vx

time {
  date
  printf 'VIOLA : #%d\n' "$(
    aws --profile s3-analise-dados s3api list-objects-v2 \
      --bucket analise-dados \
      --prefix "projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538/" \
      --query "length(Contents[?Size!='0'])"
  )"
  printf 'ESPADARTE - RUN_20240414_0030VB0082 : #%d\n' "$(
    aws --profile s3-analise-dados s3api list-objects-v2 \
      --bucket analise-dados \
      --prefix "projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/ESPADARTE/6000702270/COM20240425/RUN_20240414_0030VB0082/" \
      --query "length(Contents[?Size!='0'])"
  )"
  printf 'ESPADARTE - RUN_20240415_0030VB0083 : #%d\n' "$(
    aws --profile s3-analise-dados s3api list-objects-v2 \
      --bucket analise-dados \
      --prefix "projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/ESPADARTE/6000702270/COM20240425/RUN_20240415_0030VB0083/" \
      --query "length(Contents[?Size!='0'])"
  )"
} | cat
