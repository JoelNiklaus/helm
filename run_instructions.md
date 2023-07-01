# Run the evaluations 

Set the env variables. Decrease the MAX_EVAL_INSTANCES for faster initial results.
```bash
conda activate crfm-helm
SUITE="test"
MAX_EVAL_INSTANCES=10000
DATASETS="lex_glue"
MODELS="
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-1000_tasks-only-casehold
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-5000_tasks-only-casehold
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-10000_tasks-only-casehold
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-45000_tasks-only-casehold
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-1000_tasks-only-lexglue
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-5000_tasks-only-lexglue
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-10000_tasks-only-lexglue
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-50000_tasks-only-lexglue
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-1000_tasks-only-tc
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-5000_tasks-only-tc
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-10000_tasks-only-tc
lawinstruct/LegalLM-falcon-7b-lora@falcon-7b-max-seq-len-512_samples-50000_tasks-only-tc
"
export CUDA_VISIBLE_DEVICES=0 # make sure we only use one GPU
```

Run the evaluation for each of the models. Make sure to delete the cache before each run (rm -rf prod_env)

```bash
for MODEL in ${MODELS}; do
    echo "Running ${MODEL} on ${DATASETS}" >> ${SUITE}.log 2>&1
    nvidia-smi >> ${SUITE}.log 2>&1
    rm -rf prod_env && helm-run --local \
        -c run_specs_legal.conf \
        --enable-huggingface-models ${MODEL} \
        --models-to-run ${MODEL} \
        --groups-to-run ${DATASETS} \
        --max-eval-instances ${MAX_EVAL_INSTANCES} \
        --suite ${SUITE} >> ${SUITE}.log 2>&1
    nvidia-smi >> ${SUITE}.log 2>&1
done
```

Summarize the results
```bash
helm-summarize --suite ${SUITE}
```