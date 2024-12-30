dir=stats_CE

mkdir -p $dir

model_path=meta_models/model_stats.pkl
ar_path=AR_models/{}-single-{}.tar
config_path={}-single-{}_infer

predicate=queries/stats_queries/predicate
query_file=queries/stats_queries/all_queries.pkl
sub_plan_file=queries/stats_queries/all_sub_plan_queries_str.pkl

save=$dir/result
log=$dir/evaluate.log

python run_experiment.py --dataset stats --evaluate --ar_path $ar_path --model_path $model_path --config_path $config_path --query_file $query_file  --query_sub_plan_file $sub_plan_file --save_folder $save --query_predicate_location $predicate > $log
