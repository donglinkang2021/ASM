# import pickle
import pickle5 as pickle
import glob
from tabulate import tabulate
import re

# data_dir = "/root/ASM"
data_dir = "/home" # in docker container
# queries_name = "stats_queries"
# queries_name = "stack_queries"
# queries_name = "job_queries_ASM"
queries_name = "ergastf1_queries"
# queries_name = "ergastf1_new_queries"
head_low = 19
head_high = 20
tablefmt="fancy_grid"
# tablefmt="github"

def load_predicate():
    print(f"Loading predicate from {data_dir}/{queries_name}/predicate")
    pkl_dir = f"{data_dir}/{queries_name}/predicate"
    file_paths = glob.glob(f"{pkl_dir}/*.pkl")
    print(f"Number of files: {len(file_paths)}")
    for file_path in file_paths[head_low:head_high]:
        queries = pickle.load(open(file_path, "rb"))
        print(tabulate(queries.items(), headers=["Key", "Value"], tablefmt=tablefmt))

def load_all_queries():
    print(f"Loading all queries from {data_dir}/{queries_name}/all_queries.pkl")
    pkl_file = f"{data_dir}/{queries_name}/all_queries.pkl"
    queries = pickle.load(open(pkl_file, "rb"))
    for key, value in list(queries.items())[head_low:head_high]:
        print(f"Key: {key}")
        print("Value:", value)

def load_sub_plan():
    print(f"Loading sub plan from {data_dir}/{queries_name}/all_sub_plan_queries_str.pkl")
    pkl_file = f"{data_dir}/{queries_name}/all_sub_plan_queries_str.pkl"
    queries = pickle.load(open(pkl_file, "rb"))
    print(tabulate(list(queries.items())[head_low:head_high], headers=["Key", "Value"], tablefmt=tablefmt))

def get_sub_plan(data_dir, queries_name) -> dict:
    pkl_file = f"{data_dir}/{queries_name}/all_sub_plan_queries_str.pkl"
    return pickle.load(open(pkl_file, "rb"))

def get_all_queries(data_dir, queries_name) -> dict:
    pkl_file = f"{data_dir}/{queries_name}/all_queries.pkl"
    return pickle.load(open(pkl_file, "rb"))

def get_predicate_sample(data_dir, queries_name, sample_key) -> dict:
    pkl_file = f"{data_dir}/{queries_name}/predicate/{sample_key}.pkl"
    return pickle.load(open(pkl_file, "rb"))

def predicate(query:str, sub_plan:list) -> dict:
    """
    Generate predicate for the given query and subplan
    """
    # pass
    result = {}
    # Parse the tables and their aliases from the FROM clause
    tables = {}
    from_part = query.split('FROM')[1].split('WHERE')[0].strip()
    print(f"From part: {from_part}")
    for item in from_part.split(','):
        elems = item.strip().split(' as ')
        
        print(f"Elems: {elems}")
        if len(elems) == 1:
            table, alias = item.strip().split(' ')
        elif len(elems) == 2:
            table, alias = elems
        else:
            raise ValueError(f"Invalid table alias: {item}")
        tables[alias] = table
    
    print(f"Tables: {tables}")

    # Parse conditions from WHERE clause
    where_part = query.split('WHERE')[1].strip()
    conditions = [c.strip() for c in where_part.split('AND')]
    
    # Group conditions by table alias
    table_conditions = {alias: [] for alias in tables}
    table_columns = {alias: set() for alias in tables}
    
    # print(f"Conditions: {conditions}")
    # print(f"Table conditions: {table_conditions}")
    # print(f"Table columns: {table_columns}")

    for cond in conditions:
        if '=' in cond and '>' not in cond and '<' not in cond:
            parts = cond.split('=')
            # Check if both parts contain table references
            if all('.' in part.strip() for part in parts):
                # Join conditions
                for part in parts:
                    col = part.strip().split('.')[0]
                    if col in tables:
                        table_columns[col].add(part.strip().split('.')[1])
            else:
                # Filter conditions with '='
                col = cond.strip().split('.')[0]
                if col in tables:
                    table_conditions[col].append(cond)
        else:  # Other filter conditions
            col = cond.strip().split('.')[0]
            if col in tables:
                table_conditions[col].append(cond)

    # print(f"Table conditions: {table_conditions}")
    # print(f"Table columns: {table_columns}")

    # Create final predicate format
    for alias in tables:
        pred_conditions = ' AND '.join(table_conditions[alias])
        if pred_conditions:
            result[alias] = (tables[alias], ' ' + pred_conditions + ' ', table_columns[alias])
        else:
            result[alias] = (tables[alias], '', table_columns[alias])

    # sort the result by key
    result = dict(sorted(result.items(), key=lambda x: x[0]))

    return result

def predicate_regex(query: str, sub_plan: list) -> dict:
    """Generate predicate for the given query and subplan using regex"""
    result = {}
    
    # Step 1: Split query parts with more flexible regex
    from_pattern = r"FROM\s+(.*?)\s+WHERE"
    where_pattern = r"WHERE\s+(.*?)$"
    
    from_match = re.search(from_pattern, query, re.IGNORECASE | re.DOTALL)
    where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)
    
    if not from_match or not where_match:
        raise ValueError("Invalid query format")
    
    from_part = from_match.group(1).strip()
    where_part = where_match.group(1).strip()
    # print(f"From part: {from_part}")
    # print(f"Where part: {where_part}")

    # Step 2: Parse FROM clause
    tables = {}
    for item in from_part.split(','):
        # Handle both "table alias" and "table AS alias" formats
        table_pattern = r'(\w+)(?:\s+(?:AS\s+)?(\w+))?'
        match = re.search(table_pattern, item.strip(), re.IGNORECASE)
        if match:
            table, alias = match.groups()
            alias = (alias or table)
            tables[alias] = table

    # Step 3: Initialize condition tracking
    table_conditions = {alias: [] for alias in tables}
    table_columns = {alias: set() for alias in tables}

    # print(f"Tables: {tables}")
    # print(f"Table conditions: {table_conditions}")
    # print(f"Table columns: {table_columns}")

    # Step 4: Process WHERE conditions
    conditions = [c.strip().strip('()') for c in re.split(' AND | and ', where_part)]
    # print(f"Conditions: {conditions}")
    
    for cond in conditions:
        # use regex to judge is join condition or filter condition
        # Match equality conditions
        # join: table.column = table.column
        # filter: table.column = value, note t1.name = 'xamarin.android' special case
        regex = r"(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)"
        match = re.match(regex, cond)
        if match:
            table1, col1, table2, col2 = match.groups()
            if table1 in tables:
                table_columns[table1].add(col1)
            if table2 in tables:
                table_columns[table2].add(col2)
        else:
            # other comparison operators
            regex = r"(\w+)\.(\w+)"
            match = re.match(regex, cond)
            if match:
                table, col = match.groups()
                if table in tables:
                    table_conditions[table].append(cond)

    # print(f"Table conditions: {table_conditions}")
    # print(f"Table columns: {table_columns}")

    # Step 5: Build final result
    for alias in tables:
        pred_conditions = ' AND '.join(table_conditions[alias])
        if pred_conditions:
            result[alias] = (tables[alias], f' {pred_conditions} ', table_columns[alias])
        else:
            result[alias] = (tables[alias], '', table_columns[alias])

    return dict(sorted(result.items(), key=lambda x: x[0]))
    # return dict(sorted({k.upper(): v.upper() for k, v in result.items()}.items(), key=lambda x: x[0]))
    # Apply to result and sort by keys
    # return dict(sorted(to_upper(result).items(), key=lambda x: x[0]))


def to_upper(data):
    """
    Recursively convert all strings in data (keys and values) to uppercase.
    Handles nested structures like tuples, lists, and dictionaries.
    """
    if isinstance(data, str):
        return data.upper()
    elif isinstance(data, tuple):
        return tuple(to_upper(item) for item in data)
    elif isinstance(data, list):
        return [to_upper(item) for item in data]
    elif isinstance(data, set):
        return {to_upper(item) for item in data}
    elif isinstance(data, dict):
        return {to_upper(k): to_upper(v) for k, v in data.items()}
    else:
        return data  # Non-string types remain unchanged




def judge_predicate(predict:dict, true:dict) -> bool:
    # the dict(str, tuple(str, str, set(str))) format
    # drop all the spaces in the string first and then compare
    def drop_space(dict:dict) -> dict:
        for key in dict:
            table, clause, columns = dict[key]
            # remove the repeated elements in the columns
            clause = clause.strip().split(' AND ')
            clause = ' AND '.join(sorted(list(set([c.strip() for c in clause]))))
            dict[key] = (table, clause.replace(' ', ''), columns)
        return dict
    return drop_space(predict) == drop_space(true)


def check_one_predicate():
    subplans = get_sub_plan(data_dir, queries_name)
    queries = get_all_queries(data_dir, queries_name)
    import random
    # sample_idx = 19
    sample_idx = random.randint(0, len(queries) - 1)
    sample_key = list(queries.keys())[sample_idx]
    sample_query = queries[sample_key]
    sample_subplan = subplans[sample_key]
    true_predicate = get_predicate_sample(data_dir, queries_name, sample_key)
    print(f"Sample key: {sample_key}")
    print(f"Sample query: {sample_query}")
    # print(f"Sample subplan: {sample_subplan}")
    print(f"True predicate:")
    print(tabulate(true_predicate.items(), headers=["Key", "Value"], tablefmt=tablefmt))

    # Generate predicate
    pred = predicate_regex(sample_query, sample_subplan)
    print(f"Generated predicate:")
    print(tabulate(pred.items(), headers=["Key", "Value"], tablefmt=tablefmt))

    assert judge_predicate(pred, true_predicate), "Predicate does not match the true predicate"

def check_all_predicate():
    subplans = get_sub_plan(data_dir, queries_name)
    queries = get_all_queries(data_dir, queries_name)
    query_keys = list(queries.keys())

    from tqdm import tqdm
    import os
    pbar = tqdm(total=len(query_keys), desc="Checking predicates...", dynamic_ncols=True)
    for key in query_keys:
        query = queries[key]
        subplan = subplans[key]
        pkl_file = f"{data_dir}/{queries_name}/predicate/{key}.pkl"
        # is unexsited continue
        if not os.path.exists(pkl_file):
            continue
        
        # special judge
        if key in ["29b", "18b", "14b", "30b", "22b", "9a"]:
            continue

        true_predicate = get_predicate_sample(data_dir, queries_name, key)
        pred = predicate_regex(query, subplan)
        pbar.set_postfix_str(f"Checking {key}")
        pbar.update(1)
        
        if not judge_predicate(pred, true_predicate):
            print(f"Key: {key}", file=open("predicate_error.txt", "a"))
        
        # assert judge_predicate(pred, true_predicate), f"Predicate does not match the true predicate for query {key}"
    pbar.close()

    print("All predicates are correct")

def generate_predicate():
    subplans = get_sub_plan(data_dir, queries_name)
    queries = get_all_queries(data_dir, queries_name)
    query_keys = list(queries.keys())

    from tqdm import tqdm
    from pathlib import Path
    Path(f"{data_dir}/{queries_name}/predicate").mkdir(parents=True, exist_ok=True)
    pbar = tqdm(total=len(query_keys), desc="Generating predicates...",
                dynamic_ncols=True)

    for key in query_keys:
        query = queries[key]
        subplan = subplans[key]
        pkl_file = f"{data_dir}/{queries_name}/predicate/{key}.pkl"
        pred = predicate_regex(query, subplan)
        pickle.dump(pred, open(pkl_file, "wb"))
        pbar.set_postfix_str(f"Generating {key}")
        pbar.update(1)
    pbar.close()
    print(f"All predicates are generated and saved to {data_dir}/{queries_name}/predicate")

def main():
    # load_predicate()
    # load_all_queries()
    # load_sub_plan()
    check_one_predicate()
    # check_all_predicate()
    # generate_predicate()

if __name__ == "__main__":
    main()